# 🍪 Dulce Bocatto SI1

**Sistema de Gestión de Producción, Ventas y Reportes**
Proyecto académico desarrollado con **Django + MySQL**, como parte del curso *Sistemas de Información I (FICCT - UAGRM)*.

El sistema permite gestionar **usuarios, roles, pedidos, producción, inventario y reportes** de la microempresa *Dulce Bocatto*, automatizando los procesos internos desde la compra de insumos hasta la entrega del producto final.

---

## 🚀 Funcionalidades Principales

### 🔐 Seguridad y Usuarios

* Registro y autenticación de usuarios (`CU01`, `CU02`)
* Sistema de roles y permisos (`CU03`, `CU04`)
* Bitácora de operaciones de usuarios (`CU05`)
* Integración con modelo extendido de usuario (teléfono, email único)

### 🛒 Ventas y Clientes

* Gestión completa de pedidos y detalle de pedidos (`CU16`)
* Confirmación, pago y cancelación de pedidos (`CU17`, `CU18`)
* Descuentos aplicados por cliente o promoción
* Emisión automática de facturas (`CU19`)
* Seguimiento de envíos y entregas (`CU27`)

### 🧁 Producción y Almacén

* Control de recetas e insumos por producto (`CU31`)
* Validación de stock antes de producción (`CU32`)
* Descuento automático de insumos al producir
* Actualización de precios unitarios según costos de insumos

### 🏭 Compras y Proveedores

* Registro y recepción de compras (`CU14`)
* Kardex de movimientos de inventario (`CU15`)
* Cálculo automático de precio promedio ponderado (PPP)

### 📊 Reportes

* Reporte de ventas diarias (`CU23`)
* Reporte de entregas (`CU27`)
* Reporte de proveedores e insumos
* Exportación a PDF, CSV y HTML mediante **ReportLab**

---

## 🧱 Arquitectura del Sistema

| Capa             | Tecnología                         |
| ---------------- | ---------------------------------- |
| Backend          | Django 5.2.7 + REST Framework      |
| Frontend         | HTML, Bootstrap 5, Crispy Forms    |
| Base de Datos    | MySQL                              |
| Autenticación    | Django Auth + Roles personalizados |
| Pagos            | Stripe Checkout API                |
| Reportes PDF     | ReportLab                          |
| Configuración    | python-decouple + .env             |
| Filtros y Listas | django-filter                      |

---

## 🧰 Instalación y Configuración

```bash
# Clonar el repositorio
git clone https://github.com/alecaballero17/DulceBocattoSI1.git
cd DulceBocattoSI1

# Crear entorno virtual
python -m venv env
env\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno (.env)
cp .env.example .env
# Editar las claves según tu entorno (MySQL, Stripe, etc.)

# Aplicar migraciones y ejecutar
python manage.py migrate
python manage.py runserver
```

---

## 🧩 Casos de Uso Implementados

| Módulo     | Código      | Nombre del CU                              |
| ---------- | ----------- | ------------------------------------------ |
| Usuarios   | CU01 - CU05 | Registro, login, roles, permisos, bitácora |
| Pedidos    | CU16 - CU19 | Crear pedido, confirmar, facturar          |
| Producción | CU31 - CU32 | Receta, validación y producción            |
| Compras    | CU14 - CU15 | Registrar compra, kardex                   |
| Reportes   | CU23 - CU27 | Ventas diarias, entregas, proveedores      |

---

## 🪄 Extras Técnicos

* Scripts SQL de triggers y vistas en `/scripts/sql/`
* Templates HTML personalizados en `/templates/`
* Archivos estáticos y multimedia gestionados con `MEDIA_URL`
* Integración con `django-extensions` (`show_urls`, `shell_plus`)
* Entorno configurado mediante `.env` seguro (`python-decouple`)

---


## 🧑‍💻 Autor

**Alejandro Caballero Pereira**
Estudiante de Ingeniería Informática — *FICCT, UAGRM*
Proyecto académico guiado por el docente de *Sistemas de Información I*.

📧 Contacto: [[alecaballeropereira@gmail.com](mailto:alecaballeropereira@gmail.com)]
🔗 GitHub: [github.com/alecaballero17](https://github.com/alecaballero17)

---

## 📄 Licencia

Este proyecto tiene fines **académicos y educativos**.
Uso libre bajo licencia MIT.
