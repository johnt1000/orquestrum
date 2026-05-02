from fastapi import APIRouter, Request

router = APIRouter()


@router.get('/health')
async def health(request: Request) -> dict:
    cfg = request.app.state.config
    return {
        'status':       'ok',
        'mode':         cfg.mode,
        'root':         str(cfg.root),
        'metrics_dir':  str(cfg.metrics_dir) if cfg.metrics_dir else None,
        'targets_path': str(cfg.targets_path) if cfg.targets_path else None,
        'port':         cfg.port,
    }
