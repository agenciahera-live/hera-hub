from .access import get_agency, staff_roles


def hera_context(request):
    ctx = {}
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return ctx
    roles = staff_roles(user)
    ctx.update({
        "hera_roles": roles,
        "is_staff_user": bool(roles),
        "is_admin_user": "admin" in roles,
        "unread_notifications": user.notifications.filter(read_at__isnull=True).count(),
        "agency": get_agency(user),
    })
    creator = getattr(user, "creator", None) if not roles else None
    if creator is not None:
        from web.services import manager_contact

        ctx["manager_link"] = manager_contact(creator)
    return ctx

