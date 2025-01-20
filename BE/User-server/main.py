"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Care-bot User API Server ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛
version : 0.0.3
"""

# Libraries
from fastapi import FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder

from Database.connector import Database
from Database.models import *

from Endpoint.data_blocks import *

from utilities import *
from datetime import date

app = FastAPI()
database = Database()


# 새로운 계정을 생성하는 기능
@app.post("/accounts", status_code=status.HTTP_201_CREATED)
async def create_account(account: Account):
    # 필수 입력 정보 점검 (비밀번호, 역할, 이메일)
    if account.password is None or account.password == "":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "type": "no data",
                "loc": ["body", "password"],
                "message": "Password is required",
                "input": jsonable_encoder(account)
            }
        )
    elif account.role is None or account.role == "":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "type": "no data",
                "loc": ["body", "role"],
                "message": "Role is required",
                "input": jsonable_encoder(account, exclude={"password"})
            }
        )
    elif account.email is None or account.email == "":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "type": "no data",
                "loc": ["body", "email"],
                "message": "Email is required",
                "input": jsonable_encoder(account, exclude={"password"})
            }
        )

    # 잘못된 옵션을 선택했는지 점검
    if account.role is not None and account.role.upper() not in ["TEST", "MAIN", "SUB", "SYSTEM"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "invalid value",
                "message": "Invalid value provided for account details (role)",
                "input": jsonable_encoder(account, exclude={"password"})
            }
        )
    elif account.gender is not None and account.gender.upper() not in ["MALE", "FEMALE", "OTHER"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "invalid value",
                "message": "Invalid value provided for account details (gender)",
            }
        )

    # 중복 이메일 점검
    email_list: list = [data["email"] for data in database.get_all_email()]

    if account.email in email_list:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "already exists",
                "message": "Email is already in use",
                "input": jsonable_encoder(account, exclude={"password"})
            }
        )

    # ID 생성 및 중복 점검
    new_id: str = ""
    id_verified: bool = False

    while not id_verified:
        new_id = random_id(16, Identify.USER)
        id_list = [data["id"] for data in database.get_all_account_id()]
        if new_id not in id_list:
            id_verified = True

    # 새로운 Account 정보 생성
    hashed_password = hash_password(account.password)  # 암호화된 비밀번호
    if account.birth_date is None:  # 입력받은 생년월일을 date 타입으로 변환
        converted_birth_date = None
    else:
        if account.birth_date.year < 1900 or account.birth_date.year > 2022 or \
            account.birth_date.day < 1 or account.birth_date.day > 31 or \
            account.birth_date.month < 1 or account.birth_date.month > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "invalid value",
                    "message": "Invalid value provided for account details (birth date)",
                    "input": jsonable_encoder(account, exclude={"password"})
                }
            )
        converted_birth_date = date(
            year=account.birth_date.year,
            month=account.birth_date.month,
            day=account.birth_date.day
        )

    new_account: AccountTable = AccountTable(
        id=new_id,
        email=account.email,
        password=hashed_password,
        role=account.role.upper() if account.role is not None else "TEST",
        user_name=account.user_name,
        birth_date=converted_birth_date,
        gender=account.gender.upper() if account.gender is not None else "OTHER",
        address=account.address
    )

    # 계정 업로드
    result: bool = database.create_account(new_account)
    if result:
        return {
            "message": "New account created successfully",
            "id": new_id
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "server error",
                "message": "Failed to create new account",
                "input": jsonable_encoder(account, exclude={"password"})
            }
        )


# 가입 가능한 이메일인지 확인하는 기능
@app.post("/accounts/check-email", status_code=status.HTTP_200_OK)
async def check_email(email_check: EmailCheck):
    target_email: str = email_check.email
    email_list: list = [data["email"] for data in database.get_all_email()]

    if target_email is None or target_email == "":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "type": "no data",
                "message": "Email is required",
                "input": jsonable_encoder(email_check)
            }
        )
    elif target_email in email_list:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "already exists",
                "message": "Email is already in use",
                "input": jsonable_encoder(email_check)
            }
        )
    else:
        return {
            "message": "Email is available"
        }


# 다중 계정의 정보를 불러오는 기능
@app.get("/accounts", status_code=status.HTTP_200_OK)
async def get_all_accounts():
    account_list: list = database.get_all_accounts()
    if account_list:
        return {
            "message": "All accounts retrieved successfully",
            "result": jsonable_encoder(account_list)
        }
    else:
        return {
            "message": "No accounts found",
            "result": jsonable_encoder(account_list)
        }


@app.get("/accounts/{user_id}", status_code=status.HTTP_200_OK)
async def get_account(user_id: str):
    account_data: dict = database.get_one_account(user_id)
    if account_data:
        return {
            "message": "Account retrieved successfully",
            "result": jsonable_encoder(account_data)
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "not found",
                "message": "Account not found",
                "input": {"user_id": user_id}
            }
        )


@app.patch("/accounts/{user_id}", status_code=status.HTTP_200_OK)
async def update_account(user_id: str, updated_account: Account):
    previous_account: dict = database.get_one_account(user_id)

    # 없는 계정을 변경하려는지 확인
    if not previous_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "not found",
                "message": "Account not found",
                "input": {"user_id": user_id}
            }
        )

    # 잘못된 옵션을 선택했는지 점검
    if updated_account.role and updated_account.role.upper() not in ["TEST", "MAIN", "SUB", "SYSTEM"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "invalid value",
                "message": "Invalid value provided for account details (role)",
                "input": jsonable_encoder(updated_account)
            }
        )
    elif updated_account.gender is not None and updated_account.gender.upper() not in ["MALE", "FEMALE", "OTHER"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "invalid value",
                "message": "Invalid value provided for account details (gender)",
                "input": jsonable_encoder(updated_account)
            }
        )

    # 중복된 이메일로 변경하려는지 점검
    if updated_account.email:
        email_list: list = [data["email"] for data in database.get_all_email()]
        if updated_account.email in email_list:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "type": "already exists",
                    "message": "Email is already in use",
                    "input": jsonable_encoder(updated_account)
                }
            )

    # 입력받은 생년월일을 date 타입으로 변환
    if updated_account.birth_date is None:
        converted_birth_date = None
    else:
        if updated_account.birth_date.year < 1900 or updated_account.birth_date.year > 2022 or \
            updated_account.birth_date.day < 1 or updated_account.birth_date.day > 31 or \
            updated_account.birth_date.month < 1 or updated_account.birth_date.month > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "invalid value",
                    "message": "Invalid value provided for account details (birth date)",
                    "input": jsonable_encoder(updated_account)
                }
            )
        converted_birth_date = date(
            year=updated_account.birth_date.year,
            month=updated_account.birth_date.month,
            day=updated_account.birth_date.day
        )

    total_updated_account: AccountTable = AccountTable(
        id=user_id,
        email=updated_account.email if updated_account.email is not None else previous_account["email"],
        role=updated_account.role.upper() if updated_account.role is not None else previous_account["role"],
        user_name=updated_account.user_name if updated_account.user_name is not None else previous_account["user_name"],
        birth_date=converted_birth_date if converted_birth_date is not None else previous_account["birth_date"],
        gender=updated_account.gender.upper() if updated_account.gender is not None else previous_account["gender"],
        address=updated_account.address if updated_account.address is not None else previous_account["address"]
    )

    result: bool = database.update_one_account(user_id, total_updated_account)

    if result:
        return {
            "message": "Account updated successfully"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "server error",
                "message": "Failed to update account",
                "input": jsonable_encoder(updated_account)
            }
        )



