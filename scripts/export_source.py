"""Prepare a source-only GitHub handover; never export raw or per-record data."""
import argparse
import json
from pathlib import Path
import nbformat

ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'.py','.ps1','.sql','.md','.ipynb','.yaml','.yml','.txt'}

def export():
    files=[ROOT/name for name in ['.gitignore','README.md','requirements.txt','requirements-lock.txt','compose.yaml']]
    for folder in ['src','sql','dashboard','scripts','tests','notebooks','documentation']:
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ALLOWED)
    files.append(ROOT/'models/model_card.md')
    elements=[]
    for path in sorted(set(files)):
        relative=path.relative_to(ROOT).as_posix()
        assert not any(part in relative for part in ['.local/','artifacts/','datasets/','__pycache__/'])
        if path.suffix=='.ipynb':
            notebook=nbformat.read(path,as_version=4)
            for cell in notebook.cells:
                if cell.cell_type=='code':cell.outputs=[];cell.execution_count=None
            content=nbformat.writes(notebook)
        else:
            content=path.read_text(encoding='utf-8')
        elements.append({'path':relative,'mode':'100644','type':'blob','content':content})
    destination=ROOT/'.local/publication'
    destination.mkdir(parents=True,exist_ok=True)
    chunks=[elements[start:start+5] for start in range(0,len(elements),5)]
    for index,chunk in enumerate(chunks):
        (destination/f'payload_{index:02d}.json').write_text(json.dumps(chunk),encoding='utf-8')
    manifest={'source_files':len(elements),'payload_chunks':len(chunks),
              'paths':[entry['path'] for entry in elements],
              'raw_data_included':False,'model_binaries_included':False,'notebook_outputs_included':False}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--payload',type=int)
    args=parser.parse_args()
    if args.payload is None:
        print(json.dumps(export(),indent=2))
    else:
        print((ROOT/'.local/publication'/f'payload_{args.payload:02d}.json').read_text(encoding='utf-8'))
