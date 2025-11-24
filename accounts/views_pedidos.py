# accounts/views_pedidos.py
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import connection, models, transaction
from django.db.models import F, Q, Value
from django.db.models.functions import Coalesce, NullIf, Trim
from django.shortcuts import get_object_or_404, redirect, render

from .models_db import (
    Pedido,
    Producto,
    Sabor,
    Usuario,
    Pago,
)
from .permissions import requiere_permiso, owner_or_staff_pedido


# ============================
# Helpers SQL
# ============================

def _fetch_detalle(pedido_id: int):
    """Detalle del pedido con nombres de producto/sabor."""
    with connection.cursor() as cur:
        cur.execute("""
            SELECT dp.producto_id, p.nombre AS producto,
                   dp.sabor_id, s.nombre AS sabor,
                   dp.cantidad, dp.precio_unitario,
                   dp.sub_total
            FROM detalle_pedido dp
            JOIN producto p ON p.id = dp.producto_id
            JOIN sabor s    ON s.id = dp.sabor_id
            WHERE dp.pedido_id = %s
            ORDER BY p.nombre, s.nombre
        """, [pedido_id])
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _recalcular_total(pedido_id: int):
    """
    Recalcula el total del pedido considerando:
    total = items + costo_envio - descuentos_aplicados
    """
    with connection.cursor() as cur:
        cur.execute("""
            UPDATE pedido p
            JOIN (
              SELECT pedido_id, SUM(cantidad * precio_unitario) AS items
              FROM detalle_pedido
              WHERE pedido_id = %s
              GROUP BY pedido_id
            ) x ON x.pedido_id = p.id
            LEFT JOIN (
              SELECT pedido_id, COALESCE(SUM(monto_aplicado),0) AS descuentos
              FROM pedido_descuento
              WHERE pedido_id = %s
              GROUP BY pedido_id
            ) d ON d.pedido_id = p.id
            SET p.total = x.items + p.costo_envio - COALESCE(d.descuentos, 0)
            WHERE p.id = %s
        """, [pedido_id, pedido_id, pedido_id])




def _total_pagado(pedido_id: int) -> Decimal:
    with connection.cursor() as cur:
        cur.execute("SELECT COALESCE(SUM(monto),0) FROM pago WHERE pedido_id=%s", [pedido_id])
        (suma,) = cur.fetchone()
    return Decimal(suma or 0)


# ============================
# CUxx – Pedidos pendientes
# ============================

@login_required
@requiere_permiso("PEDIDO_READ")
def pedidos_pendientes(request):
    qs = (
        Pedido.objects.select_related("cliente")
        .filter(estado="PENDIENTE")
        .order_by("-created_at", "-id")
    )
    return render(request, "accounts/pedidos_pendientes.html", {"pedidos": qs})


# ============================
# Detalle de pedido
# ============================

@login_required
@requiere_permiso("PEDIDO_READ")
def pedido_detalle(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    detalle = _fetch_detalle(pedido.id)
    pagos = list(
        Pago.objects.filter(pedido_id=pedido.id)
        .select_related("registrado_por")
        .order_by("-created_at")
        .values(
            "id", "metodo", "monto", "referencia",
            "created_at", "registrado_por__nombre"
        )
    )
    total_pagado = _total_pagado(pedido.id)
    saldo = (pedido.total or 0) - total_pagado

    # Es dueño
    es_duenio = False
    if request.user.is_authenticated and pedido.cliente and pedido.cliente.usuario:
        es_duenio = (
            (pedido.cliente.usuario.email or "").lower()
            == (request.user.email or "").lower()
        )

    puede_editar = es_duenio and pedido.estado not in ("ENTREGADO", "CANCELADO")

    return render(request, "accounts/pedido_detalle.html", {
        "pedido": pedido,
        "detalle": detalle,
        "pagos": pagos,
        "total_pagado": total_pagado,
        "saldo_pendiente": saldo,
        "es_duenio": es_duenio,
        "puede_editar": puede_editar,
    })


# ============================
# Editar pedido (dueño o staff)
# ============================

@login_required
@owner_or_staff_pedido
def pedido_editar(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    productos = list(Producto.objects.filter(activo=True)
                     .order_by("nombre")
                     .values("id", "nombre", "precio_unitario"))

    sabores = list(Sabor.objects.filter(activo=True)
                   .order_by("nombre")
                   .values("id", "nombre"))

    if request.method == "POST":
        filas = int(request.POST.get("filas", "0"))
        items = []

        for i in range(filas):
            pid = request.POST.get(f"p_{i}")
            sid = request.POST.get(f"s_{i}")
            cant = request.POST.get(f"c_{i}")
            prec = request.POST.get(f"u_{i}")

            if not (pid and sid and cant and prec):
                continue

            pid, sid = int(pid), int(sid)
            cant, prec = Decimal(cant), Decimal(prec)

            if cant <= 0 or prec < 0:
                messages.error(request, "Cantidad y precio inválidos.")
                return redirect("pedido_editar", pedido_id=pedido.id)

            items.append((pid, sid, cant, prec))

        with transaction.atomic():
            with connection.cursor() as cur:
                if items:
                    cur.execute(
                        """
                        DELETE FROM detalle_pedido
                        WHERE pedido_id=%s
                          AND (producto_id, sabor_id) NOT IN (
                             """ + ",".join(["(%s,%s)"] * len(items)) + """
                          )
                        """,
                        [pedido.id] + [x for t in [(p, s) for p, s, _, _ in items] for x in t]
                    )
                else:
                    cur.execute("DELETE FROM detalle_pedido WHERE pedido_id=%s", [pedido.id])

                for p_id, s_id, cant, pu in items:
                    cur.execute("""
                    INSERT INTO detalle_pedido
                      (pedido_id, producto_id, sabor_id, cantidad, precio_unitario)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                       cantidad=VALUES(cantidad),
                       precio_unitario=VALUES(precio_unitario)
                    """, [pedido.id, p_id, s_id, str(cant), str(pu)])

            _recalcular_total(pedido.id)

        messages.success(request, "Pedido actualizado.")
        return redirect("pedido_detalle", pedido_id=pedido.id)

    detalle = _fetch_detalle(pedido.id)
    return render(request, "accounts/pedido_editar.html", {
        "pedido": pedido,
        "detalle": detalle,
        "productos": productos,
        "sabores": sabores,
    })


# ============================
# CU15 – Pedidos confirmados
# ============================

@login_required
@requiere_permiso("PEDIDO_READ")
def pedidos_confirmados(request):
    ESTADOS = ["CONFIRMADO", "EN_PRODUCCION", "LISTO_ENTREGA", "ENTREGADO"]

    qs = Pedido.objects.filter(estado__in=ESTADOS).order_by("-created_at", "-id")

    # Filtrar por dueño si no es admin
    if not (request.user.is_staff or request.user.is_superuser):
        try:
            app_user = Usuario.objects.get(email=request.user.email)
            qs = qs.filter(cliente__usuario=app_user)
        except Usuario.DoesNotExist:
            empty_page = Paginator(Pedido.objects.none(), 15).get_page(1)
            return render(request, "accounts/pedidos_confirmados.html", {
                "pedidos": empty_page.object_list,
                "page_obj": empty_page,
                "q": "",
                "estados_confirmados": ESTADOS,
            })

    qs = qs.select_related("cliente", "cliente__usuario").annotate(
        cliente_nombre=Coalesce(
            NullIf(Trim(F("cliente__nombre")), Value("")),
            NullIf(Trim(F("cliente__usuario__nombre")), Value("")),
            F("cliente__usuario__email"),
            output_field=models.CharField(),
        )
    )

    q = request.GET.get("q", "").strip()
    if q:
        if q.isdigit():
            qs = qs.filter(Q(id=int(q)) | Q(cliente_nombre__icontains=q))
        else:
            qs = qs.filter(cliente_nombre__icontains=q)

    page_obj = Paginator(qs, 15).get_page(request.GET.get("page"))

    return render(request, "accounts/pedidos_confirmados.html", {
        "pedidos": page_obj.object_list,
        "page_obj": page_obj,
        "q": q,
        "estados_confirmados": ESTADOS,
    })


# ============================
# CU16 – Registrar pago
# ============================

@login_required
def pago_registrar(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    es_admin = request.user.is_staff or request.user.is_superuser
    puede_cliente = False

    try:
        app_user = Usuario.objects.get(email=request.user.email)
        puede_cliente = pedido.cliente.usuario_id == app_user.id
    except Usuario.DoesNotExist:
        pass

    if not es_admin and not puede_cliente:
        messages.error(request, "No tienes permisos para esto.")
        return redirect("pedido_detalle", pedido_id=pedido.id)

    if request.method == "POST":
        metodo = request.POST.get("metodo", "").upper()
        monto = request.POST.get("monto")
        referencia = request.POST.get("referencia", "").strip()

        METODOS_VALIDOS = {"EFECTIVO", "QR", "TRANSFERENCIA", "STRIPE"}
        if metodo not in METODOS_VALIDOS:
            messages.error(request, "Método inválido.")
            return redirect("pago_registrar", pedido_id=pedido.id)

        try:
            monto = Decimal(monto)
        except:
            messages.error(request, "Monto inválido.")
            return redirect("pago_registrar", pedido_id=pedido.id)

        if monto <= 0:
            messages.error(request, "Monto debe ser mayor a cero.")
            return redirect("pago_registrar", pedido_id=pedido.id)

        if not puede_cliente:
            app_user = Usuario.objects.order_by("id").first()

        with connection.cursor() as cur:
            cur.execute("""
                INSERT INTO pago (pedido_id, metodo, monto, referencia, registrado_por_id, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, [pedido.id, metodo, str(monto), referencia or None, app_user.id])

        messages.success(request, "Pago registrado.")
        return redirect("pedido_detalle", pedido_id=pedido.id)

    total_pagado = _total_pagado(pedido.id)
    saldo = (pedido.total or 0) - total_pagado

    return render(request, "accounts/pago_form.html", {
        "pedido": pedido,
        "total_pagado": total_pagado,
        "saldo_pendiente": saldo,
    })


# ============================
# CLIENTE: marcar pedido como recibido
# ============================

@login_required
def pedido_recibido(request, pedido_id):
    """
    El cliente marca su pedido como ENTREGADO.
    Permite solo si: pertenece al usuario y está CONFIRMADO o LISTO_ENTREGA.
    """
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    if not pedido.cliente or not pedido.cliente.usuario:
        messages.error(request, "No puedes confirmar este pedido.")
        return redirect("pedidos_confirmados")

    cliente_email = (pedido.cliente.usuario.email or "").lower()
    user_email = (request.user.email or "").lower()

    # Si no es dueño ni admin → no puede confirmar
    if cliente_email != user_email and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "No puedes confirmar este pedido.")
        return redirect("pedidos_confirmados")

    if pedido.estado not in ["CONFIRMADO", "LISTO_ENTREGA"]:
        messages.warning(request, "Este pedido no puede marcarse como recibido todavía.")
        return redirect("pedidos_confirmados")

        # 4) Marcar como ENTREGADO
    pedido.estado = "ENTREGADO"
    pedido.save(update_fields=["estado"])

    messages.success(
        request,
        "¡Gracias! Marcamos tu pedido como ENTREGADO. "
        "Ahora puedes calificarlo."
    )
    # Te mando directo al formulario de calificación (CU29)
    return redirect("calificar_entrega", pedido_id=pedido.id)


