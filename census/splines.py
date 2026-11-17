# SPDX-License-Identifier: AGPL-3.0-or-later
"""Restricted centered natural splines and full-covariance joint Wald tests."""
import ast
import re
import numpy as np
import pandas as pd
import patsy
import statsmodels.api as sm
from scipy.stats import chi2

# Set from the fixed Round 27 experiment, never inferred at runtime.
# Criterion 376ce69: failed size .137–.1825 in four cells.
JOINT_WALD_VALIDATED = False


def has_spline(formula):
    return bool(re.search(r'\bcr\s*\(', str(formula)))


def spline_formula(formula):
    """Validate cr(variable, df=3|4|5) and remove intercept redundancy.

    Only the documented shorthand is supported. Explicit knots, nested spline
    expressions and other constraints need separate design/validation work.
    """
    if not has_spline(formula):
        return formula
    if has_spline(formula.split("~",1)[0]):
        raise ValueError("cr is supported only for covariates on the right-hand side")
    codes=[]
    for side in (patsy.ModelDesc.from_formula(formula).lhs_termlist,
                 patsy.ModelDesc.from_formula(formula).rhs_termlist):
        for term in side:
            for factor in term.factors:
                if has_spline(factor.code): codes.append(factor.code)
    replacements={}
    for code in codes:
        node=ast.parse(code,mode='eval').body
        if (not isinstance(node,ast.Call) or not isinstance(node.func,ast.Name) or node.func.id!='cr'
            or len(node.args)!=1 or not isinstance(node.args[0],ast.Name)):
            raise ValueError('cr requires one plain variable and df=3, 4 or 5; nested spline expressions are unsupported')
        kw={k.arg:k.value for k in node.keywords}
        df=kw.get('df')
        if (set(kw)-{'df','constraints'} or len(kw)!=len(node.keywords) or not isinstance(df,ast.Constant)
            or type(df.value) is not int or df.value not in (3,4,5)):
            raise ValueError('cr requires explicit df=3, 4 or 5 and default quantile knots')
        constraints=kw.get('constraints')
        if constraints is not None and (not isinstance(constraints,ast.Constant) or constraints.value!='center'):
            raise ValueError('cr supports only centered constraints')
        replacements[code]=f'cr({node.args[0].id}, df={df.value}, constraints="center")'
    # Patsy normalizes code whitespace. Matching each restricted call in the
    # source keeps the rest of the user's formula and all old formulas intact.
    def replace(match):
        code=match.group(0)
        normalized=patsy.ModelDesc.from_formula('~'+code).rhs_termlist[-1].factors[0].code
        return replacements[normalized]
    return re.sub(r'\bcr\s*\([^()]*\)',replace,formula)


def frozen_refit(full, data, model, weights=None, exposure=None, trials=None, scale=None):
    """Rebuild both designs using the full fit's stateful patsy transforms."""
    X=patsy.build_design_matrices([full.model.data.orig_exog.design_info],data,NA_action='raise')[0]
    if np.linalg.matrix_rank(X) < X.shape[1]:
        raise ValueError("rank-deficient frozen spline replicate design")
    y_info=full.model.data.orig_endog.design_info
    y=np.asarray(patsy.build_design_matrices([y_info],data,NA_action='raise')[0],float)[:,0]
    if model=='ols': result=sm.OLS(y,X).fit()
    elif model=='wls': result=sm.WLS(y,X,weights=np.asarray(data[weights],float)).fit()
    else:
        family=sm.families.Binomial() if model=='binomial' else sm.families.Poisson()
        kwargs={'var_weights':np.asarray(trials,float)} if model=='binomial' else {'exposure':np.asarray(data[exposure],float) if exposure else None}
        result=sm.GLM(y,X,family=family,**kwargs).fit(**({'scale':scale} if scale else {}))
    return pd.Series(np.asarray(result.params,float),index=full.params.index)


def variable_columns(design_info, variable, data_columns):
    """Standalone terms only: exclude interactions and mixed-variable I(...)."""
    columns=[]
    for term in design_info.terms:
        if len(term.factors)!=1: continue
        node=ast.parse(term.factors[0].code,mode='eval')
        names={n.id for n in ast.walk(node) if isinstance(n,ast.Name)} & set(data_columns)
        # Q("name with spaces") is also a single variable.
        for n in ast.walk(node):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='Q' and n.args and isinstance(n.args[0],ast.Constant):
                names.add(n.args[0].value)
        if names=={variable}:
            sl=design_info.term_name_slices[term.name()]
            columns.extend(design_info.column_names[sl])
    return columns


def joint_wald(result, variable):
    """HC3 / sampling / conservative chi-squared test, without a pseudoinverse."""
    columns=result.diagnostics.get('joint_columns',{}).get(variable,[])
    if not columns: raise ValueError(f'no standalone design columns for joint variable {variable!r}')
    if not result.diagnostics.get('joint_full_rank',False):
        raise ValueError('rank-deficient model design; joint hypothesis not tested')
    target=result.diagnostics['interval_target']
    cov=result.diagnostics['sampling_covariance' if target=='these_areas' else 'joint_model_covariance'].loc[columns,columns].to_numpy(float)
    if target=='conservative':
        sampling=result.diagnostics['sampling_covariance'].loc[columns,columns].to_numpy(float)
        if result.diagnostics.get('joint_has_replicates',False): cov=cov+sampling
    b=result.coefficients.set_index('term').loc[columns,'estimate'].to_numpy(float)
    if not np.isfinite(cov).all() or not np.isfinite(b).all() or np.linalg.matrix_rank(cov)<len(b):
        raise ValueError('singular or non-finite joint covariance; joint hypothesis not tested (no pseudoinverse)')
    np.linalg.cholesky(cov)
    W=float(b@np.linalg.solve(cov,b))
    return dict(estimate=W,se=None,p_two_sided=float(chi2.sf(W,len(b))),ci_lower=None,ci_upper=None,df=len(b))
