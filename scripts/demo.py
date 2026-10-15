"""Exercise the running API, preserving observed successes and limitations."""
import argparse
import json
from pathlib import Path
import httpx


def main():
    parser=argparse.ArgumentParser();parser.add_argument('repository_path');parser.add_argument('--output',default='capsules/demo.json');parser.add_argument('--dependency');parser.add_argument('--version');args=parser.parse_args()
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=3900,trust_env=False) as client:
        def post(route,payload):
            response=client.post('/api/'+route,json=payload);response.raise_for_status();return response.json()
        snapshot=post('scan',{'repository_path':str(Path(args.repository_path).resolve())})
        print(f"Scanned {len(snapshot['dependencies'])} dependencies",flush=True)
        snapshot=post('analyze',snapshot);print('AI:',snapshot['ai_status'],flush=True)
        if args.dependency and args.version:
            # Deliberately no executable trust acknowledgement from this demo helper.
            result=post('verify',{'scan_id':snapshot['scan_id'],'dependency_name':args.dependency,'proposed_version':args.version,'trusted_repository':False})
            print('Verification:',result['verification_status'],flush=True)
        capsule=post('capsule',{'scan_id':snapshot['scan_id']})
        out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(capsule,indent=2))
        print('Saved',out)


if __name__=='__main__':main()
