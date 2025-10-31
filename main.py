"""
Aplicação principal FastAPI para gestão de slots e picking
"""
from fastapi import FastAPI, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import os
from models.database import get_db, Base, engine
from models.slot import Slot
from models.device import Device, DeviceStatus
from models.movement import Movement
from routers import slots_router, assign_router, picking_router, scan_router, devices_router
from services.assignment_service import AssignmentService
from services.picking_service import PickingService

# Configurar templates Jinja2
template_env = Environment(loader=FileSystemLoader("templates"))

def render_template(template_name: str, context: dict):
    """Renderiza um template Jinja2 e retorna HTMLResponse"""
    template = template_env.get_template(template_name)
    html_content = template.render(**context)
    return HTMLResponse(content=html_content)

# Criar diretório storage se não existir
os.makedirs("storage", exist_ok=True)

# Criar app FastAPI
app = FastAPI(title="Gestão de Slots e Picking", description="MVP Local para gestão de slots e picking")

# Incluir routers (depois das rotas HTML para não conflitar)
app.include_router(slots_router)
app.include_router(assign_router)
app.include_router(picking_router)
app.include_router(scan_router)
app.include_router(devices_router)


@app.on_event("startup")
async def startup_event():
    """Inicializar banco de dados na startup"""
    Base.metadata.create_all(bind=engine)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard principal"""
    # Contar slots totais
    total_slots = db.query(func.count(Slot.id)).scalar() or 0

    # Contar slots livres
    free_slots = db.query(func.count(Slot.id)).filter(Slot.occupied == False).scalar() or 0

    # Contar devices em estoque
    devices_in_stock = db.query(func.count(Device.id)).filter(
        Device.status == DeviceStatus.IN_STOCK
    ).scalar() or 0

    # Buscar últimos movimentos
    recent_movements = db.query(Movement).order_by(
        Movement.ts.desc()
    ).limit(10).all()

    # Buscar informações dos slots nos movimentos
    for movement in recent_movements:
        if movement.to_slot_id:
            slot = db.query(Slot).filter(Slot.id == movement.to_slot_id).first()
            if slot:
                movement.to_slot_human_code = slot.human_code
        if movement.from_slot_id:
            slot = db.query(Slot).filter(Slot.id == movement.from_slot_id).first()
            if slot:
                movement.from_slot_human_code = slot.human_code

    return render_template("index.html", {
        "request": request,
        "total_slots": total_slots,
        "free_slots": free_slots,
        "devices_in_stock": devices_in_stock,
        "recent_movements": recent_movements
    })


@app.get("/assign", response_class=HTMLResponse)
async def assign_page(request: Request):
    """Página de alocação automática"""
    return render_template("assign.html", {"request": request})


@app.get("/picking", response_class=HTMLResponse)
async def picking_page(request: Request):
    """Página de picking"""
    return render_template("picking.html", {"request": request})


@app.get("/slots/page", response_class=HTMLResponse)
async def available_slots_page(request: Request):
    """Página de slots livres"""
    return render_template("available_slots.html", {"request": request})


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """Página de consulta"""
    return render_template("search.html", {"request": request})


# Rotas para renderizar templates parciais HTMX (conflitam com rotas de API, mas HTML tem prioridade se vier depois)
@app.post("/assign/auto/htmx", response_class=HTMLResponse)
async def assign_devices_auto_template(
    request: Request,
    device_ids: Optional[str] = Form(None),
    csv_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Renderiza template parcial com resultado da alocação"""
    # Processar device_ids
    device_ids_list = []
    if device_ids:
        # Separar por quebra de linha ou vírgula
        device_ids_list = [d.strip() for d in device_ids.replace(',', '\n').split('\n') if d.strip()]

    # Processar CSV se fornecido
    if csv_file:
        import csv
        import io
        contents = await csv_file.read()
        text = contents.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(text))
        for row in csv_reader:
            if row:
                device_ids_list.extend([d.strip() for d in row if d.strip()])

    # Remover duplicatas
    device_ids_list = list(dict.fromkeys(device_ids_list))

    if not device_ids_list:
        return render_template("partials/assign_result.html", {
            "request": request,
            "assigned": [],
            "failed": [],
            "current_position": None,
            "error": "Nenhum device_id fornecido"
        })

    # Chamar serviço
    result = AssignmentService.assign_devices_auto(db, device_ids_list)

    return render_template("partials/assign_result.html", {
        "request": request,
        "assigned": result.get("assigned", []),
        "failed": result.get("failed", []),
        "current_position": result.get("current_position"),
        "error": result.get("error")
    })


@app.post("/picking/plan/htmx", response_class=HTMLResponse)
async def create_picking_plan_template(
    request: Request,
    device_ids: Optional[str] = Form(None),
    csv_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Renderiza template parcial com plano de picking"""
    # Processar device_ids
    device_ids_list = []
    if device_ids:
        device_ids_list = [d.strip() for d in device_ids.replace(',', '\n').split('\n') if d.strip()]

    # Processar CSV se fornecido
    if csv_file:
        import csv
        import io
        contents = await csv_file.read()
        text = contents.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(text))
        for row in csv_reader:
            if row:
                device_ids_list.extend([d.strip() for d in row if d.strip()])

    # Remover duplicatas
    device_ids_list = list(dict.fromkeys(device_ids_list))

    if not device_ids_list:
        return render_template("partials/picking_result.html", {
            "request": request,
            "route": [],
            "total_distance": 0.0,
            "start_position": None,
            "error": "Nenhum device_id fornecido"
        })

    # Chamar serviço
    result = PickingService.create_picking_plan(db, device_ids_list)

    # Adicionar flag picked=False para cada item
    route = result.get("route", [])
    for item in route:
        item["picked"] = False

    return render_template("partials/picking_result.html", {
        "request": request,
        "route": route,
        "total_distance": result.get("total_distance", 0.0),
        "start_position": result.get("start_position")
    })


@app.get("/slots/available/htmx", response_class=HTMLResponse)
async def get_available_slots_template(
    request: Request,
    limit: int = 50,
    start_rua: Optional[int] = None,
    start_prateleira: Optional[str] = None,
    start_linha: Optional[int] = None,
    start_coluna: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Renderiza template parcial com slots livres"""
    # Determinar ponto inicial
    if start_rua and start_prateleira and start_linha and start_coluna:
        from services.codecs import row_to_letter
        row_letter = row_to_letter(start_linha)
        human_code = f"R{start_rua}-{start_prateleira}-{row_letter}-C{start_coluna}"
        start_slot = db.query(Slot).filter(Slot.human_code == human_code).first()
    else:
        start_slot = AssignmentService.get_default_start_slot(db)

    if not start_slot:
        # Se não encontrar ponto inicial, retornar slots livres sem ordenação
        slots = db.query(Slot).filter(Slot.occupied == False).limit(limit).all()
        return render_template("partials/slots_result.html", {
            "request": request,
            "slots": slots
        })

    # Buscar slots livres e calcular distâncias
    from services.distance_service import DistanceService
    free_slots = db.query(Slot).filter(Slot.occupied == False).all()

    slots_with_distance = [
        (slot, DistanceService.calculate_distance(start_slot, slot))
        for slot in free_slots
    ]

    # Ordenar por distância
    slots_with_distance.sort(key=lambda x: x[1])

    # Limitar resultados
    slots_with_distance = slots_with_distance[:limit]

    slots = [s for s, _ in slots_with_distance]

    # Buscar informações relacionadas (aisle e shelf)
    from models.aisle import Aisle
    from models.shelf import Shelf
    for slot in slots:
        slot.aisle = db.query(Aisle).filter(Aisle.id == slot.aisle_id).first()
        slot.shelf = db.query(Shelf).filter(Shelf.id == slot.shelf_id).first()

    return render_template("partials/slots_result.html", {
        "request": request,
        "slots": slots
    })


@app.get("/devices/search/htmx", response_class=HTMLResponse)
async def search_devices_template(
    request: Request,
    query: str,
    db: Session = Depends(get_db)
):
    """Renderiza template parcial com resultados da busca"""
    # Buscar por device_id
    from models.device import Device
    from models.slot import Slot
    
    devices_by_id = db.query(Device).filter(
        Device.device_id.ilike(f"%{query}%")
    ).all()

    # Buscar por human_code do slot
    slots = db.query(Slot).filter(
        Slot.human_code.ilike(f"%{query}%")
    ).all()
    slot_ids = [s.id for s in slots]
    devices_by_slot = db.query(Device).filter(
        Device.slot_id.in_(slot_ids)
    ).all() if slot_ids else []

    # Combinar resultados (sem duplicatas)
    all_devices = {}
    for device in devices_by_id:
        all_devices[device.id] = device
    for device in devices_by_slot:
        all_devices[device.id] = device

    results = []
    for device in all_devices.values():
        slot_human_code = None
        row = None
        col = None

        if device.slot_id:
            slot = db.query(Slot).filter(Slot.id == device.slot_id).first()
            if slot:
                slot_human_code = slot.human_code
                row = slot.row_index
                col = slot.col_index

        results.append({
            "id": device.id,
            "device_id": device.device_id,
            "status": device.status,
            "slot_id": device.slot_id,
            "slot_human_code": slot_human_code,
            "row": row,
            "col": col
        })

    return render_template("partials/search_result.html", {
        "request": request,
        "results": results
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

