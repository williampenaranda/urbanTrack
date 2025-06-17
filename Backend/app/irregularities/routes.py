# app/irregularities/routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError # Para manejar duplicados en la clave primaria compuesta
from sqlalchemy.sql import func
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point
from datetime import datetime # Importa datetime para actualizar ultimo_like_atz|
from app.database import get_db
from app.models.entities import ReportedIrregularity, Usuario, IrregularityVote as DBIrregularityVote
from app.models.models import IrregularityCreate, IrregularityResponse, IrregularityVoteResponse  
from app.auth.dependencies import get_current_user # Para obtener el usuario autenticado

router = APIRouter()

@router.post(
    "/report",
    response_model=IrregularityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reportar una nueva irregularidad o accidente",
    description="Permite a un usuario autenticado reportar una irregularidad en la vía pública (accidente, desvío, etc.). El reporte es anónimo."
)
async def report_irregularity(
    irregularity: IrregularityCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    point = Point(irregularity.longitud, irregularity.latitud)
    db_location = from_shape(point, srid=4326)

    db_irregularity = ReportedIrregularity(
        titulo=irregularity.titulo,
        descripcion=irregularity.descripcion,
        ubicacion=db_location,
        likes=0,
        dislikes=0,
        activa=True, 
    )

    db.add(db_irregularity)
    db.commit()
    db.refresh(db_irregularity) 

    db_irregularity.ubicacion = to_shape(db_irregularity.ubicacion)
    
    return db_irregularity


@router.get(
    "/search/{irregularity_id}",
    response_model=IrregularityResponse,
    summary="Obtener detalles de una irregularidad por ID",
    description="Permite consultar la información de una irregularidad específica por su ID."
)
async def get_irregularity_details(
    irregularity_id: int,
    db: Session = Depends(get_db)
):
    """
    Recupera una irregularidad por su ID.
    """
    irregularity = db.query(ReportedIrregularity).filter(ReportedIrregularity.id == irregularity_id).first()
    if not irregularity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Irregularidad no encontrada"
        )
    irregularity.ubicacion = to_shape(irregularity.ubicacion)
    return irregularity

@router.get(
    "/active",
    response_model=list[IrregularityResponse],
    summary="Obtener todas las irregularidades activas",
    description="Lista todas las irregularidades que están marcadas como activas en el sistema."
)
async def get_active_irregularities(
    db: Session = Depends(get_db)
):
    """
    Recupera todas las irregularidades activas.
    """
    irregularities = db.query(ReportedIrregularity).filter(ReportedIrregularity.activa == True).all()
    for irreg in irregularities:
        irreg.ubicacion = to_shape(irreg.ubicacion)
    return irregularities

@router.post(
    "/vote/{irregularity_id}/like",
    response_model=IrregularityVoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dar 'Me gusta' a una irregularidad",
    description="Permite a un usuario dar un voto positivo a una irregularidad reportada. Un usuario solo puede votar una vez por irregularidad."
)
async def like_irregularity(
    irregularity_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Registra un voto 'like' para una irregularidad.
    Actualiza el contador de likes y el campo 'ultimo_like_at' de la irregularidad.
    """
    irregularity = db.query(ReportedIrregularity).filter(ReportedIrregularity.id == irregularity_id).first()
    if not irregularity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Irregularidad no encontrada"
        )

    # Verificar si el usuario ya votó por esta irregularidad
    existing_vote = db.query(DBIrregularityVote).filter(
        DBIrregularityVote.irregularity_id == irregularity_id, # <--- CAMBIO AQUÍ: 'irregularity_id'
        DBIrregularityVote.user_id == current_user.id  
    ).first()

    if existing_vote:
        if existing_vote.is_like:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya has dado 'Me gusta' a esta irregularidad."
            )
        else: # Si ya dio dislike, cambia a like
            existing_vote.is_like = True # <-- ¡CAMBIO IMPORTANTE AQUÍ!
            existing_vote.created_at = func.now()
            irregularity.dislikes -= 1 # Reduce el dislike
            irregularity.likes += 1    # Incrementa el like
            irregularity.ultimo_like_at = datetime.now() # Actualiza el tiempo del último like
            db.add(existing_vote)
            db.add(irregularity)
            db.commit()
            db.refresh(existing_vote)
            return existing_vote
    
    # Si no ha votado, crea un nuevo voto 'like'
    new_vote = DBIrregularityVote(
        irregularity_id=irregularity_id, # <--- CAMBIO AQUÍ: 'irregularity_id'
        user_id=current_user.id,         # <--- CAMBIO AQUÍ: 'user_id'
        is_like=True     
    )
    
    try:
        db.add(new_vote)
        irregularity.likes += 1
        irregularity.ultimo_like_at = datetime.now() # Actualiza el tiempo del último like
        db.add(irregularity) # Marca la irregularidad para ser actualizada
        db.commit()
        db.refresh(new_vote)
        return new_vote
    except IntegrityError:
        # Esto debería ser prevenido por la verificación previa, pero es un buen respaldo
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya has votado por esta irregularidad."
        )


@router.post(
    "/vote/{irregularity_id}/dislike",
    response_model=IrregularityVoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dar 'No me gusta' a una irregularidad",
    description="Permite a un usuario dar un voto negativo a una irregularidad reportada. Un usuario solo puede votar una vez por irregularidad."
)
async def dislike_irregularity(
    irregularity_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Registra un voto 'dislike' para una irregularidad.
    Actualiza el contador de dislikes.
    """
    irregularity = db.query(ReportedIrregularity).filter(ReportedIrregularity.id == irregularity_id).first()
    if not irregularity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Irregularidad no encontrada"
        )

    # Verificar si el usuario ya votó por esta irregularidad
    existing_vote = db.query(DBIrregularityVote).filter(
        DBIrregularityVote.irregularity_id == irregularity_id, # <--- CAMBIO AQUÍ: 'irregularity_id'
        DBIrregularityVote.user_id == current_user.id    
    ).first()

    if existing_vote:
        if not existing_vote.is_like:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya has dado 'No me gusta' a esta irregularidad."
            )
        else: # Si ya dio like, cambia a dislike
            existing_vote.is_like = False # <-- ¡CAMBIO IMPORTANTE AQUÍ!
            existing_vote.created_at = func.now()
            irregularity.likes -= 1    # Reduce el like
            irregularity.dislikes += 1 # Incrementa el dislike
            # NOTA: No se actualiza 'ultimo_like_at' al dar dislike.
            db.add(existing_vote)
            db.add(irregularity)
            db.commit() 
            db.refresh(existing_vote)
            return existing_vote

    # Si no ha votado, crea un nuevo voto 'dislike'
    new_vote = DBIrregularityVote(
        irregularity_id=irregularity_id, # <--- CAMBIO AQUÍ: 'irregularity_id'
        user_id=current_user.id,         # <--- CAMBIO AQUÍ: 'user_id'
        is_like=False  
    )
    
    try:
        db.add(new_vote)
        irregularity.dislikes += 1
        db.add(irregularity) # Marca la irregularidad para ser actualizada
        db.commit()
        db.refresh(new_vote)
        return new_vote
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya has votado por esta irregularidad."
        )