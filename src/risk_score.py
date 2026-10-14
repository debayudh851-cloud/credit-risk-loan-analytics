"""PRD risk bands apply to the rounded integer score, not raw probability."""
import numpy as np
import pandas as pd

def score(probabilities):
    p = np.asarray(probabilities, dtype=float)
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('Probabilities must be finite and in [0, 1]')
    s = np.rint(p * 100).astype(int)
    return pd.DataFrame({'default_probability': p, 'risk_score': s,
                         'risk_category': np.select([s <= 33, s <= 66],
                                                   ['Low Risk', 'Medium Risk'], default='High Risk')})
