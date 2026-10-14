from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'datasets'
OUT = ROOT / 'artifacts'
SEED = 42
AS_OF = '2024-06-30'

def prepare():
    for directory in [DATA, OUT, ROOT / 'models', OUT / 'figures', OUT / 'sql']:
        directory.mkdir(parents=True, exist_ok=True)
