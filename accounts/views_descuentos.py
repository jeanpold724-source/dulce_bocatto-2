from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection, transaction
from django.shortcuts import get_object_or_404, redirect, render

from .models_db import Descuento, Pedido, PedidoDescuento
from .forms import DescuentoForm
from .permissions import requiere_permiso
from .views_pedidos import _recalcular_total


# ============================
# CU30 - Gestionar promociones y descuentos
# ============================

@login_required
@requiere_permiso("PEDIDO_READ")
def descuentos_list(request):
    qs = Descuento.objects.all().order_by("-activo", "nombre")
    return render(request, "accounts/descuentos_list.html", {"descuentos": qs})


@login_required
@requiere_permiso("PEDIDO_WRITE")
def descuento_form(request, descuento_id=None):
    if descuento_id:
        descuento = get_object_or_404(Descuento, pk=descuento_id)
    else:
        descuento = None

    if request.method == "POST":
        form = DescuentoForm(request.POST, instance=descuento)
        if form.is_valid():
            form.save()
            messages.success(request, "Descuento guardado correctamente.")
            return redirect("descuentos_list")
    else:
        form = DescuentoForm(instance=descuento)

    return render(request, "accounts/descuento_form.html", {
        "form": form,
        "descuento": descuento,
    })


@login_required
@requiere_permiso("PEDIDO_WRITE")
def descuento_toggle_activo(request, descuento_id):
    descuento = get_object_or_404(Descuento, pk=descuento_id)
    descuento.activo = not descuento.activo
    descuento.save(update_fields=["activo"])
    messages.success(
        request,
        f"Descuento '{descuento.nombre}' ahora está "
        + ("ACTIVO" if descuento.activo else "INACTIVO")
    )
    return redirect("descuentos_list")


# ============================
# Aplicar descuento a un pedido concreto
# ============================

def _calcular_base_pedido(pedido_id: int) -> Decimal:
    """Base sobre la que se calcula porcentaje (items + envío)."""
    with connection.cursor() as cur:
        cur.execute("""
            SELECT 
              COALESCE(SUM(dp.cantidad * dp.precio_unitario), 0) AS items,
              COALESCE(p.costo_envio, 0) AS envio
            FROM pedido p
            LEFT JOIN detalle_pedido dp ON dp.pedido_id = p.id
            WHERE p.id = %s
            GROUP BY p.id
        """, [pedido_id])
        row = cur.fetchone()
    if not row:
        return Decimal("0")
    items, envio = row
    return Decimal(items) + Decimal(envio)


@login_required
@requiere_permiso("PEDIDO_WRITE")
def aplicar_descuento_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    descuentos = Descuento.objects.filter(activo=True).order_by("nombre")

    if request.method == "POST":
        desc_id = request.POST.get("descuento_id")
        if not desc_id:
            messages.error(request, "Debes seleccionar un descuento.")
            return redirect("aplicar_descuento_pedido", pedido_id=pedido.id)

        descuento = get_object_or_404(Descuento, pk=desc_id)

        base = _calcular_base_pedido(pedido.id)

        if base <= 0:
            messages.error(request, "El pedido no tiene items para aplicar descuento.")
            return redirect("aplicar_descuento_pedido", pedido_id=pedido.id)

        # Calcula monto_aplicado según tipo
        if descuento.tipo == Descuento.TIPO_FIJO:
            monto = min(Decimal(descuento.valor), base)
        else:  # PORCENTAJE
            monto = (base * Decimal(descuento.valor) / Decimal("100")).quantize(
                Decimal("0.01")
            )

        with transaction.atomic():
            pedido_desc, _ = PedidoDescuento.objects.update_or_create(
                pedido=pedido,
                descuento=descuento,
                defaults={"monto_aplicado": monto},
            )
            _recalcular_total(pedido.id)

        messages.success(
            request,
            f"Se aplicó el descuento '{descuento.nombre}' por Bs. {monto} "
            f"al pedido #{pedido.id}."
        )
        return redirect("pedido_detalle", pedido_id=pedido.id)

    return render(request, "accounts/pedido_aplicar_descuento.html", {
        "pedido": pedido,
        "descuentos": descuentos,
    })
