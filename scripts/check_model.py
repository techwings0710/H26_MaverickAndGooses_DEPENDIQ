"""Genuine inference check; does not inject mock responses."""
import argparse
import json
from ai.gemma_client import GemmaClient, GemmaError
from backend.scanner import scan


def main():
    parser=argparse.ArgumentParser();parser.add_argument('repository_path');args=parser.parse_args()
    snapshot=scan(args.repository_path)
    dependency=next((d for d in snapshot.dependencies if d.risk_level!='low'),None)
    if not dependency:raise SystemExit('No flagged dependency. Use a repository with observed risk evidence.')
    try:
        client=GemmaClient();result=client.recommend(dependency)
        print(json.dumps({'dependency':dependency.name,'model_info':client.info,'recommendation':result.model_dump()},indent=2))
    except GemmaError as exc:raise SystemExit(str(exc)) from exc


if __name__=='__main__':main()
