from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import crud, schemas, dependencies, security

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

@router.post("/login", response_model=schemas.LoginResponse)
def login(request: schemas.LoginRequest, db: Session = Depends(dependencies.get_db)):
    """Log in with phone number + password. Only admin-created users can log in."""
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid phone number or password",
    )

    user = crud.get_user_by_phone(db, request.phone_number)
    # Same error for unknown user / no password / wrong password to avoid leaking which phones exist.
    if user is None or not user.password_hash:
        raise invalid
    if not security.verify_password(request.password, user.password_hash):
        raise invalid
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive. Please contact admin.",
        )

    return schemas.LoginResponse(
        access_token=security.create_access_token(user.id),
        user=schemas.User.model_validate(user),
    )

@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    request: schemas.ChangePasswordRequest,
    db: Session = Depends(dependencies.get_db),
    current_user: dict = Depends(dependencies.get_current_user),
):
    user = crud.get_user(db, current_user['uid'])
    if not user.password_hash or not security.verify_password(request.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    user.password_hash = security.hash_password(request.new_password)
    db.commit()
    return None
