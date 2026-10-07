"""Safe-mode pipeline entrypoint. Provider implementations are intentionally explicit."""
from __future__ import annotations
import argparse
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--kind', choices=['short', 'long'], required=True)
    p.add_argument('--publish-mode', choices=['private', 'unlisted'], default='private')
    args = p.parse_args()
    cfg = yaml.safe_load((ROOT / 'config/channel.yaml').read_text())
    if cfg['publishing']['public_publish_enabled']:
        raise RuntimeError('Public publishing is disabled in this starter until explicit review.')
    print(f"Preparing {args.kind} for {cfg['channel']['url']}")
    print(f"Timezone: {cfg['channel']['timezone']} | upload mode: {args.publish_mode}")
    print('Next implementation steps: research -> script -> voice/avatar -> captions -> render -> YouTube private upload -> audit.')
    print('No external upload is performed by this scaffold until provider adapters and secrets are configured.')

if __name__ == '__main__':
    main()
