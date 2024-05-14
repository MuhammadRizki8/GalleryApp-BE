from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal
import models
import schemas
from dependencies import get_current_user, get_db

purchase_router = APIRouter(prefix="/purchase", tags=["purchase"])

@purchase_router.post("/", response_model=schemas.Purchase)
async def create_purchase(purchase: schemas.PurchaseCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    photo = db.query(models.Photo).filter(models.Photo.id_photo == purchase.id_photo).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Check if the photo's author is the current user
    if photo.id_author == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot purchase your own photo")

    # Check if the user has already purchased this photo
    existing_purchase = db.query(models.Purchase).filter(
        models.Purchase.id_user == current_user.id,
        models.Purchase.id_photo == purchase.id_photo
    ).first()
    if existing_purchase:
        raise HTTPException(status_code=400, detail="You have already purchased this photo")

    wallet = db.query(models.Wallet).filter(models.Wallet.id_user == current_user.id).first()
    if wallet.balance < photo.price:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    new_purchase = models.Purchase(
        id_user=current_user.id,
        id_photo=purchase.id_photo,
        amount=photo.price,
    )
    
    wallet.balance -= photo.price

    db.add(new_purchase)
    db.commit()
    db.refresh(new_purchase)
    db.refresh(wallet)  # Ensure the wallet is updated in the session

    return new_purchase

@purchase_router.get("/user/{user_id}", response_model=list[schemas.PurchaseDetail])
async def get_purchases_by_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user's purchases")

    purchases = db.query(models.Purchase).filter(models.Purchase.id_user == user_id).all()
    if not purchases:
        raise HTTPException(status_code=404, detail="No purchases found for this user")

    purchases_with_details = []
    for purchase in purchases:
        photo = db.query(models.Photo).filter(models.Photo.id_photo == purchase.id_photo).first()
        purchase_with_detail = schemas.PurchaseDetail(
            id_purchase=purchase.id_purchase,
            id_user=purchase.id_user,
            id_photo=purchase.id_photo,
            amount=purchase.amount,
            create_at=purchase.create_at,
            photo=schemas.PhotoDetail(
                id_photo=photo.id_photo,
                title=photo.title,
                description=photo.description,
                price=photo.price,
                id_author=photo.id_author,
                create_at=photo.create_at,
                update_at=photo.update_at
            )
        )
        purchases_with_details.append(purchase_with_detail)

    return purchases_with_details
