from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
ROOT=Path(__file__).resolve().parents[1]
paths=[ROOT/'notebooks'/name for name in sys.argv[1:]] if len(sys.argv)>1 else sorted((ROOT/'notebooks').glob('*.ipynb'))
for path in paths:
    print('Executing',path.name,flush=True)
    notebook=nbformat.read(path,as_version=4)
    NotebookClient(notebook,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}}).execute()
    nbformat.write(notebook,path)
print(f'{len(paths)} notebooks executed without cell errors.')
