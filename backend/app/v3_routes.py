"""HIVE V3 API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app import panel_identity
from app.moduller import project_engine as pe

router = APIRouter(prefix="/api/v3", tags=["V3"])


def _current_user(request: Request) -> dict[str, Any]:
    user = getattr(request.state, "hive_user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def _require(request: Request, module: str, action: str) -> dict[str, Any]:
    user = _current_user(request)
    if not panel_identity.has_permission(user.get("role", ""), module, action):
        raise HTTPException(status_code=403, detail="Permission denied")
    return user


class ProjectCreateBody(BaseModel):
    name: str
    sector: str
    domain: str = ""
    business_brief: str = ""
    design: dict[str, Any] = Field(default_factory=dict)
    deploy_mode: str = "hive_cloud"
    status: str = "draft"


class ProjectUpdateBody(BaseModel):
    name: str | None = None
    sector: str | None = None
    domain: str | None = None
    business_brief: str | None = None
    design: dict[str, Any] | None = None
    deploy_mode: str | None = None
    status: str | None = None
    pages: list[dict[str, Any]] | None = None
    theme: dict[str, Any] | None = None
    navigation: list[dict[str, str]] | None = None


class CreativeSuggestBody(BaseModel):
    sector: str
    business_brief: str = ""
    creative_brief: str = ""
    use_llm: bool = True


class PageUpdateBody(BaseModel):
    title: str | None = None
    slug: str | None = None
    type: str | None = None
    status: str | None = None
    seo: dict[str, Any] | None = None
    sections: list[dict[str, Any]] | None = None


class PublishBody(BaseModel):
    build: bool = True


class DomainBindBody(BaseModel):
    domain: str
    include_www: bool = True


class ExportBody(BaseModel):
    build: bool = False


class FillBlocksBody(BaseModel):
    use_llm: bool = True


@router.get("/projects/health")
def projects_health():
    return pe.health()


@router.get("/sector-packs")
def list_sector_packs(request: Request):
    _require(request, "projects", "view")
    from app.moduller import sector_packs
    sectors = sector_packs.list_sectors()
    packs = []
    for s in sectors:
        pack = sector_packs.load_pack(s)
        if pack:
            packs.append({
                "sector_id": s,
                "pack_id": pack.get("pack_id"),
                "display_name": pack.get("display_name"),
                "page_count": len(pack.get("default_pages") or []),
            })
    return {"success": True, "packs": packs}


@router.post("/creative-director/suggest")
def creative_director_suggest(body: CreativeSuggestBody, request: Request):
    _require(request, "projects", "view")
    return pe.creative_suggest(
        sector=body.sector,
        business_brief=body.business_brief,
        creative_brief=body.creative_brief,
        use_llm=body.use_llm,
    )


@router.get("/projects")
def list_projects_v3(
    request: Request,
    status: str = "",
    sector: str = "",
    search: str = "",
    limit: int = 50,
    offset: int = 0,
):
    _require(request, "projects", "view")
    return pe.list_projects(status=status, sector=sector, search=search, limit=limit, offset=offset)


@router.get("/projects/active")
def get_active_project_v3(request: Request):
    _require(request, "projects", "view")
    from app.moduller import project_context
    return project_context.get_active_project_payload()


@router.post("/projects/{project_id}/set-active")
def set_active_project_v3(project_id: str, request: Request):
    _require(request, "projects", "edit")
    from app.moduller import project_context
    result = project_context.set_active_project(project_id)
    if not result.get("success"):
        code = 404 if result.get("error") == "not_found" else 400
        raise HTTPException(status_code=code, detail=result.get("error") or "set_failed")
    return result


@router.post("/projects")
def create_project_v3(body: ProjectCreateBody, request: Request):
    _require(request, "projects", "create")
    result = pe.create_project(
        name=body.name,
        sector=body.sector,
        domain=body.domain,
        business_brief=body.business_brief,
        design=body.design,
        deploy_mode=body.deploy_mode,
        status=body.status,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message") or result.get("error"))
    return result


@router.get("/projects/{project_id}")
def get_project_v3(project_id: str, request: Request):
    _require(request, "projects", "view")
    result = pe.get_project(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.patch("/projects/{project_id}")
def patch_project_v3(project_id: str, body: ProjectUpdateBody, request: Request):
    _require(request, "projects", "edit")
    fields = body.model_dump(exclude_unset=True)
    result = pe.update_project(project_id, fields)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.delete("/projects/{project_id}")
def delete_project_v3(project_id: str, request: Request):
    _require(request, "projects", "delete")
    result = pe.delete_project(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.post("/projects/{project_id}/fill-blocks")
def fill_blocks_v3(project_id: str, body: FillBlocksBody, request: Request):
    _require(request, "projects", "edit")
    result = pe.fill_blocks(project_id, use_llm=body.use_llm)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.post("/projects/{project_id}/retro-seed")
def retro_seed_v3(project_id: str, request: Request):
    _require(request, "projects", "edit")
    result = pe.retro_seed(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.post("/projects/{project_id}/export-astro")
def export_astro_v3(project_id: str, body: ExportBody, request: Request):
    _require(request, "projects", "edit")
    result = pe.export_astro(project_id, build=body.build)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error") or "export_failed")
    return result


@router.post("/projects/{project_id}/export/astro")
def export_astro_site_v3(project_id: str, request: Request):
    _require(request, "projects", "edit")
    result = pe.export_astro_site(project_id)
    if not result.get("success"):
        code = 404 if result.get("error") == "not_found" else 400
        raise HTTPException(status_code=code, detail=result.get("error") or "export_failed")
    return result


@router.get("/projects/{project_id}/export/astro/status")
def export_astro_status_v3(project_id: str, request: Request):
    _require(request, "projects", "view")
    result = pe.get_astro_export_status(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error") or "not_found")
    return result


@router.post("/projects/{project_id}/export/astro/validate")
def validate_astro_export_v3(project_id: str, request: Request):
    _require(request, "projects", "edit")
    result = pe.validate_astro_export(project_id)
    if not result.get("success"):
        code = 404 if result.get("error") == "not_found" else 400
        raise HTTPException(status_code=code, detail=result.get("error") or result.get("message") or "validate_failed")
    return result


@router.get("/projects/{project_id}/export/astro/validate/status")
def validate_astro_status_v3(project_id: str, request: Request):
    _require(request, "projects", "view")
    result = pe.get_astro_validate_status(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error") or "not_found")
    return result


@router.get("/projects/{project_id}/publish-gate")
def publish_gate_v3(project_id: str, request: Request):
    _require(request, "projects", "view")
    result = pe.get_publish_gate(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error") or "not_found")
    return result


@router.post("/projects/{project_id}/export/astro/build")
def run_astro_build_v3(project_id: str, request: Request):
    _require(request, "projects", "edit")
    result = pe.run_astro_build(project_id)
    if not result.get("success"):
        code = 404 if result.get("error") == "not_found" else 400
        raise HTTPException(status_code=code, detail=result.get("error") or "build_failed")
    return result


@router.get("/projects/{project_id}/export/astro/build/status")
def astro_build_status_v3(project_id: str, request: Request):
    _require(request, "projects", "view")
    result = pe.get_astro_build_status(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error") or "not_found")
    return result


@router.post("/projects/{project_id}/publish/prepare")
def prepare_publish_v3(project_id: str, request: Request):
    _require(request, "projects", "edit")
    result = pe.prepare_publish_artifact(project_id)
    if not result.get("success"):
        code = 404 if result.get("error") == "not_found" else 400
        raise HTTPException(status_code=code, detail=result.get("error") or "prep_failed")
    return result


@router.get("/projects/{project_id}/publish/prepare/status")
def prepare_publish_status_v3(project_id: str, request: Request):
    _require(request, "projects", "view")
    result = pe.get_prepare_publish_status(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error") or "not_found")
    return result


@router.post("/projects/{project_id}/deploy/hive-cloud")
def deploy_hive_cloud_v3(project_id: str, request: Request):
    _require(request, "projects", "edit")
    result = pe.deploy_hive_cloud(project_id)
    if not result.get("success"):
        code = 404 if result.get("error") == "not_found" else 400
        raise HTTPException(status_code=code, detail=result.get("error") or "deploy_failed")
    return result


@router.get("/projects/{project_id}/deploy/hive-cloud/status")
def deploy_hive_cloud_status_v3(project_id: str, request: Request):
    _require(request, "projects", "view")
    result = pe.get_hive_cloud_deploy_status(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error") or "not_found")
    return result


@router.post("/projects/{project_id}/domain/bind")
def bind_domain_v3(project_id: str, body: DomainBindBody, request: Request):
    _require(request, "projects", "edit")
    result = pe.bind_project_domain(project_id, body.domain, include_www=body.include_www)
    if not result.get("success"):
        code = 404 if result.get("error") == "not_found" else 400
        raise HTTPException(status_code=code, detail=result.get("error") or "bind_failed")
    return result


@router.get("/projects/{project_id}/domain/status")
def domain_status_v3(project_id: str, request: Request):
    _require(request, "projects", "view")
    result = pe.get_domain_binding_status(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error") or "not_found")
    return result


@router.post("/projects/{project_id}/deploy/production/plan")
def plan_production_deploy_v3(project_id: str, request: Request):
    _require(request, "projects", "edit")
    result = pe.plan_production_deploy(project_id)
    if not result.get("success"):
        code = 404 if result.get("error") == "not_found" else 400
        raise HTTPException(status_code=code, detail=result.get("error") or "plan_failed")
    return result


@router.get("/projects/{project_id}/deploy/production/status")
def production_deploy_status_v3(project_id: str, request: Request):
    _require(request, "projects", "view")
    result = pe.get_production_deploy_status(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error") or "not_found")
    return result


@router.get("/projects/{project_id}/deploy/production/nginx-preview")
def production_nginx_preview_v3(project_id: str, request: Request):
    _require(request, "projects", "view")
    result = pe.get_production_nginx_preview(project_id)
    if not result.get("success"):
        code = 404 if result.get("error") == "not_found" else 400
        raise HTTPException(status_code=code, detail=result.get("error") or "preview_failed")
    return result


@router.post("/projects/{project_id}/deploy/production/apply-script")
def generate_production_apply_script_v3(project_id: str, request: Request):
    _require(request, "projects", "edit")
    result = pe.generate_production_apply_script(project_id)
    if not result.get("success"):
        code = 404 if result.get("error") == "not_found" else 400
        raise HTTPException(status_code=code, detail=result.get("error") or "script_failed")
    return result


@router.get("/projects/{project_id}/deploy/production/apply-script/status")
def production_apply_script_status_v3(project_id: str, request: Request):
    _require(request, "projects", "view")
    result = pe.get_production_apply_script_status(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error") or "not_found")
    return result


@router.post("/projects/{project_id}/publish")
def publish_project_v3(project_id: str, body: PublishBody, request: Request):
    _require(request, "projects", "edit")
    result = pe.publish_project(project_id, build=body.build)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error") or "publish_failed")
    return result


@router.patch("/projects/{project_id}/pages/{page_id}")
def patch_page_v3(project_id: str, page_id: str, body: PageUpdateBody, request: Request):
    _require(request, "projects", "edit")
    fields = body.model_dump(exclude_unset=True)
    result = pe.update_page(project_id, page_id, fields)
    if not result.get("success"):
        err = result.get("error", "not_found")
        raise HTTPException(status_code=404, detail=err)
    return result
