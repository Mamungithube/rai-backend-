from .oauth import GoogleLoginView
from .signup import (
    signup_initiate,
    signup_verify,
    signup_finalize,
    resend_otp,
)
from .session import (
    MyTokenObtainPairView,
    logout_view,
)
from .profile import (
    get_profile,
    update_profile,
    delete_account,
)
from .password import (
    password_reset_request,
    password_reset_confirm,
    change_password,
)
from .identity import (
    initiate_email_change,
    verify_email_change,
    resend_email_change_otp,
    initiate_phone_change,
    verify_phone_change,
    resend_phone_change_otp,
)

__all__ = [
    "GoogleLoginView",
    "signup_initiate",
    "signup_verify",
    "signup_finalize",
    "resend_otp",
    "MyTokenObtainPairView",
    "logout_view",
    "get_profile",
    "update_profile",
    "delete_account",
    "password_reset_request",
    "password_reset_confirm",
    "change_password",
    "initiate_email_change",
    "verify_email_change",
    "resend_email_change_otp",
    "initiate_phone_change",
    "verify_phone_change",
    "resend_phone_change_otp",
]
