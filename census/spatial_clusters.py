# SPDX-License-Identifier: AGPL-3.0-or-later
"""Spatial-cluster inference (Round 26): only IM with eight groups passed.

The numerical kernels match the immutable pre-run validation implementation;
regression tests compare them and independent statsmodels calculations. Validation
was on MI/NY independent/spatial fields for OLS and binomial, not EIV or Poisson.
"""
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.cluster.vq import kmeans2
from scipy.special import expit
from scipy.stats import norm, t
from pyproj import Transformer
from .spatial_hac import unit_coordinates

SPATIAL_CLUSTERS_VALIDATED = {"cr1_t": False, "im": True, "wcr": False}
VALIDATED_CLUSTER_COUNTS = {"cr1_t": (), "im": (8,), "wcr": ()}
DEFAULT_SPATIAL_CLUSTERS = {"k": 8, "method": "im"}
WEBB = np.array([-np.sqrt(1.5), -1., -np.sqrt(.5), np.sqrt(.5), 1., np.sqrt(1.5)])

def cluster_points(coords, k, seed=20261126):
    """50 kmeans++ restarts, lowest SSE among solutions with >=5 members/group.

    Coordinates are the same representative points as the Round 22 generator,
    projected to EPSG:5070. Labels canonicalized by centroid x then y. No outcomes.
    """
    xy = np.column_stack(Transformer.from_crs(4326,5070,always_xy=True).transform(coords.lon,coords.lat))
    if type(k) is not int or k<2 or len(xy)<5*k or not np.isfinite(xy).all():
        raise ValueError('k needs at least five finite points per cluster')
    rng = np.random.default_rng(seed); choices=[]
    for restart in range(50):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            centers, labels = kmeans2(xy,k,iter=100,minit='++',rng=rng)
        counts=np.bincount(labels,minlength=k)
        if np.min(counts)<5: continue
        sse=float(np.sum((xy-centers[labels])**2))
        order=np.lexsort((centers[:,1],centers[:,0])); relabel=np.empty(k,int);relabel[order]=np.arange(k)
        choices.append((sse,restart,relabel[labels]))
    if not choices: raise ValueError(f'no admissible k={k} solution among 50 fixed restarts')
    return min(choices,key=lambda c:(c[0],c[1]))[2]

def group_sums(values, labels):
    values=np.asarray(values,float);labels=np.asarray(labels)
    _,inv=np.unique(labels,return_inverse=True)
    result=np.zeros((int(inv.max())+1,)+values.shape[1:])
    np.add.at(result,inv,values)
    return result

def cluster_covariance(scores, bread_inv, labels):
    scores=np.asarray(scores,float);bread_inv=np.asarray(bread_inv,float)
    n,k=scores.shape; grouped=group_sums(scores,labels);g=len(grouped)
    if g<2 or n<=k or not np.isfinite(scores).all(): raise ValueError('invalid cluster covariance design')
    factor=g/(g-1)*(n-1)/(n-k)
    return factor*bread_inv@(grouped.T@grouped)@bread_inv.T

def fit_components(X,y,design,trials=None):
    if design=='linear':
        bread=np.linalg.inv(X.T@X);b=bread@X.T@y;mu=X@b
        scores=X*(y-mu)[:,None];h=np.einsum('ij,jk,ik->i',X,bread,X)
        hc3=bread@((scores/(1-h[:,None])).T@(scores/(1-h[:,None])))@bread
    else:
        fit=sm.GLM(y,X,family=sm.families.Binomial(),var_weights=trials).fit(scale='X2')
        if not fit.converged: raise ValueError('binomial fit did not converge')
        b=np.asarray(fit.params);mu=np.asarray(fit.fittedvalues)
        w=trials*mu*(1-mu);bread=np.linalg.inv(X.T@(w[:,None]*X))
        scores=X*(trials*(y-mu))[:,None];h=w*np.einsum('ij,jk,ik->i',X,bread,X)
        hc3=bread@((scores/(1-h[:,None])).T@(scores/(1-h[:,None])))@bread
    if not np.isfinite(b).all() or not np.isfinite(hc3).all(): raise ValueError('nonfinite fit')
    return b,bread,scores,hc3

def im_test(X,y,labels,design,trials=None,term=1,level=.90):
    betas=[]
    for label in np.unique(labels):
        keep=labels==label
        b,_,_,_=fit_components(X[keep],y[keep],design,None if trials is None else trials[keep])
        betas.append(b[term])
    est=float(np.mean(betas));se=float(np.std(betas,ddof=1)/np.sqrt(len(betas)))
    critical=t.ppf((1+level)/2,len(betas)-1)
    return est,se,est-critical*se,est+critical*se

def _restricted_scores(X,y,design,trials,term,null):
    nuisance=np.delete(X,term,axis=1)
    offset=X[:,term]*null
    if design=='linear':
        resid=y-offset-nuisance@np.linalg.lstsq(nuisance,y-offset,rcond=None)[0]
        return X*resid[:,None]
    # Offset GLM nuisance MLE, with a stable one-intercept Newton solve for validation.
    if nuisance.shape[1]==1 and np.all(nuisance[:,0]==1):
        mean=np.clip(np.average(y,weights=trials),1e-10,1-1e-10)
        a=float(np.log(mean/(1-mean))-np.average(offset,weights=trials))
        for _ in range(100):
            mu=expit(a+offset);information=np.sum(trials*mu*(1-mu))
            if information<=0: raise ValueError('restricted fit singular')
            step=np.clip(np.sum(trials*(y-mu))/information,-5,5);a+=step
            if abs(step)<1e-10:break
        else:raise ValueError('restricted fit did not converge')
        mu=expit(a+offset)
    else:
        f=sm.GLM(y,nuisance,family=sm.families.Binomial(),var_weights=trials,offset=offset).fit()
        if not f.converged:raise ValueError('restricted fit did not converge')
        mu=np.asarray(f.fittedvalues)
    return X*(trials*(y-mu))[:,None]

def wild_cluster_test(X,y,labels,design,trials=None,term=1,null=0.,weights=None,
                      components=None,interval=False,level=.90):
    """Restricted WCR / Score2-Wald; supports one coefficient, no ACS sampling SE."""
    labels=np.asarray(labels);g=len(np.unique(labels));n,k=X.shape
    if weights is None: raise ValueError('explicit frozen bootstrap weights required')
    weights=np.asarray(weights,float)
    if weights.shape!=(999,g):raise ValueError('999 cluster weight draws required')
    b,bread,scores,_=components or fit_components(X,y,design,trials)
    cov=cluster_covariance(scores,bread,labels);se=float(np.sqrt(cov[term,term]));est=float(b[term])
    if not np.isfinite(se) or se<=0:raise ValueError('bootstrap has no finite positive SE')
    c=bread[:,term];factor=g/(g-1)*(n-1)/(n-k)
    if design=='linear':
        info_groups=group_sums(X[:,:,None]*X[:,None,:],labels)
        correction=info_groups@c
    else:
        # Score2-Wald studentizes restricted perturbations with unrestricted scores.
        projection=group_sums(scores,labels)@c
        denominator=np.sqrt(factor*((weights*projection[None,:])**2).sum(axis=1))
    def pvalue(value):
        grouped=group_sums(_restricted_scores(X,y,design,trials,term,value),labels)
        rhs=weights@grouped;delta=rhs@bread.T
        if design=='linear':
            influences=weights*(grouped@c)[None,:]-delta@correction.T
            denom=np.sqrt(factor*np.sum(influences**2,axis=1))
        else:denom=denominator
        if not np.isfinite(denom).all() or (denom<=0).any():raise ValueError('invalid bootstrap studentization')
        ts=delta[:,term]/denom;obs=(est-value)/se
        return float((1+np.count_nonzero(np.abs(ts)>=abs(obs)))/(len(weights)+1))
    p=pvalue(null);lo=hi=None
    if interval:
        # Invert endpoints of the same restricted test about the estimate.
        # Fixed brackets/tolerance; disconnected confidence sets are not characterized.
        ends=[]
        for direction in (-1,1):
            inside=est;step=se*t.ppf((1+level)/2,g-1);outside=est+direction*step
            for _ in range(20):
                if pvalue(outside)<1-level:break
                step*=2;outside=est+direction*step
            else:raise ValueError('bootstrap CI not bracketed in 20 doublings')
            for _ in range(24):
                middle=(inside+outside)/2
                if pvalue(middle)>=1-level:inside=middle
                else:outside=middle
            ends.append((inside+outside)/2)
        lo,hi=ends
    return {'estimate':est,'p_value':p,'ci_lower':lo,'ci_upper':hi,'se_cr1':se,'df':g-1}

def check_config(config):
    """Validate the explicit, hashed k/method pair (booleans are not integers)."""
    if not isinstance(config, dict) or set(config) != {"k", "method"}:
        raise ValueError("spatial_clusters must contain exactly k and method")
    if type(config["k"]) is not int or config["k"] < 2:
        raise ValueError("spatial_clusters.k must be an integer >=2")
    if not isinstance(config["method"], str) or config["method"] not in SPATIAL_CLUSTERS_VALIDATED:
        raise ValueError("spatial_clusters.method must be cr1_t, im or wcr")
    return config


def spatial_clusters(geoids, level, acs_year, k, seed=20261126):
    """Fixed geographic assignment; output GEOID/lon/lat/cluster plus attrs provenance.

    Input IDs are sorted before k-means to make assignment invariant to row order.
    No outcome or covariate values enter the clustering. All groups need >=5 units.
    """
    ids = sorted(set(map(str, geoids)))
    coords, provenance = unit_coordinates(ids, level, acs_year)
    assignment = coords.copy()
    assignment["cluster"] = cluster_points(coords, k, seed)
    assignment.attrs.update(provenance=provenance, k=k, seed=seed, crs="EPSG:5070")
    return assignment


def assignment_for_frame(frame, coords, config):
    """Compute assignment before formula/outcome complete-case filtering."""
    check_config(config)
    if "GEOID" not in frame:
        raise ValueError("spatial_clusters requires GEOID")
    ids = sorted(set(frame.GEOID.astype(str)))
    if coords is None:
        lengths = set(map(len, ids))
        level = "county" if lengths == {5} else "tract" if lengths == {11} else None
        if level is None or "Year" not in frame:
            raise ValueError("spatial_clusters needs county/tract GEOIDs and Year, or explicit coordinates")
        return spatial_clusters(ids, level, int(frame.Year.max()), config["k"])
    if not {"GEOID", "lon", "lat"} <= set(coords):
        raise ValueError("coordinates require GEOID, lon, lat")
    coords = coords.assign(GEOID=coords.GEOID.astype(str))
    if coords.GEOID.duplicated().any():
        raise ValueError("duplicate coordinate GEOIDs")
    ordered = coords.set_index("GEOID").reindex(ids).reset_index()
    if ordered[["lon", "lat"]].isna().any().any():
        raise ValueError("missing coordinates for analysed GEOIDs")
    ordered["cluster"] = cluster_points(ordered, config["k"])
    ordered.attrs.update(k=config["k"], seed=20261126, crs="EPSG:5070")
    return ordered


def inference_table(full, data, n_trials, model, config, assignment, target, level, se_sampling):
    """Return method-specific coefficients and diagnostics, without changing old fits.

    IM's between-cluster one-sample SE is recorded as se_cluster_mean, not as an
    additive full-sample se_model. WCR has no scalar reported SE. Both refuse ACS
    replicates in fit_replicate and use only population-target inference.
    """
    from .models import _table
    X = np.asarray(full.model.exog, float); y = np.asarray(full.model.endog, float)
    rows = np.asarray(full.model.data.row_labels)
    ids = data.loc[rows, "GEOID"].astype(str)
    labels = assignment.set_index("GEOID").loc[ids, "cluster"].to_numpy(int)
    counts = pd.DataFrame({"GEOID":ids.to_numpy(),"cluster":labels}).drop_duplicates().groupby("cluster").size()
    if len(counts) != config["k"] or counts.min() < 5:
        raise ValueError("spatial_clusters requires >=5 analysed counties/tracts in every fixed cluster")
    if np.linalg.matrix_rank(X) != X.shape[1]:
        raise ValueError("spatial-cluster full design is rank deficient")
    trials = np.asarray(n_trials, float)[rows] if model == "binomial" else None
    b,bread,scores,_ = fit_components(X,y,"linear" if model=="ols" else "binomial",trials)
    terms = list(full.params.index); g = config["k"]; critical = t.ppf((1+level)/2,g-1)
    info = {**config,"df":g-1,"critical_value":float(critical),"seed":20261126,
            "assignment":dict(zip(assignment.GEOID.astype(str),map(int,assignment.cluster))),
            "analysed_cluster_sizes":{str(k):int(v) for k,v in counts.items()},
            "validated":bool(SPATIAL_CLUSTERS_VALIDATED[config["method"]] and
                             g in VALIDATED_CLUSTER_COUNTS[config["method"]])}
    if config["method"] == "cr1_t":
        se = np.sqrt(np.diag(cluster_covariance(scores,bread,labels)))
        table = _table(full.params,pd.Series(se,index=terms),se_sampling,level,target)
        basis={"population":"se_model","these_areas":"se_sampling","conservative":"se_total"}[target]
        table["ci_lower"] = table.estimate-critical*table[basis]
        table["ci_upper"] = table.estimate+critical*table[basis]
        table["p_value"] = 2*t.sf(np.abs(table.estimate/table[basis]),g-1)
    elif config["method"] == "im":
        betas=[]
        for label in np.unique(labels):
            keep=labels==label
            if np.linalg.matrix_rank(X[keep]) != X.shape[1]:
                raise ValueError("IM requires the same full-rank design in every cluster; state fixed effects may be unidentifiable within geographic clusters")
            fit,_,_,_=fit_components(X[keep],y[keep],"linear" if model=="ols" else "binomial",None if trials is None else trials[keep])
            betas.append(fit)
        mean=np.mean(betas,axis=0);se=np.std(betas,axis=0,ddof=1)/np.sqrt(g)
        table=pd.DataFrame({"term":terms,"estimate":mean,"se_model":np.nan,"se_sampling":np.nan,
                            "se_total":np.nan,"se_cluster_mean":se,"ci_lower":mean-critical*se,
                            "ci_upper":mean+critical*se,"p_value":2*t.sf(np.abs(mean/se),g-1)})
        info["cluster_estimates"] = np.asarray(betas).tolist()
    else:
        rng=np.random.default_rng(20261126);weights=WEBB[rng.integers(0,6,size=(999,g))]
        result=[]
        for j,term in enumerate(terms):
            z=wild_cluster_test(X,y,labels,"linear" if model=="ols" else "binomial",trials,
                                term=j,weights=weights,components=(b,bread,scores,None),interval=True,level=level)
            result.append({"term":term,"estimate":z["estimate"],"se_model":np.nan,"se_sampling":np.nan,
                           "se_total":np.nan,"ci_lower":z["ci_lower"],"ci_upper":z["ci_upper"],"p_value":z["p_value"]})
        table=pd.DataFrame(result);info["bootstrap_draws"]=999
        info["critical_value"] = None
    if config["method"] != "wcr":table["df"]=g-1
    return table,info
