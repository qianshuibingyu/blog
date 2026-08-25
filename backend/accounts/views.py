import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


def _request_data(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    data = _request_data(request)
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    user = authenticate(request, username=username, password=password)

    if user is None:
        return JsonResponse({"detail": "用户名或密码错误。"}, status=401)

    if not user.is_active:
        return JsonResponse({"detail": "该账号已被停用。"}, status=403)

    login(request, user)
    return JsonResponse({
        "id": user.id,
        "username": user.get_username(),
        "is_staff": user.is_staff,
    })


@csrf_exempt
@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return JsonResponse({"detail": "已退出登录。"})


@require_http_methods(["GET"])
def me_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "未登录。"}, status=401)

    return JsonResponse({
        "id": request.user.id,
        "username": request.user.get_username(),
        "is_staff": request.user.is_staff,
    })
