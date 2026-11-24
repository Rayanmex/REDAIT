from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.http import JsonResponse

from .models import Noticia, Categoria, ImagenNoticia
from .forms import NoticiaForm, CategoriaForm


# ============================================================
# VISTAS PÚBLICAS
# ============================================================

def lista_noticias(request):
    """Listado público de noticias."""
    ahora = timezone.now()
    qs = (
        Noticia.objects
        .filter(estado='publicada', fecha_publicacion__lte=ahora)
        .filter(Q(fecha_expiracion__isnull=True) | Q(fecha_expiracion__gte=ahora))
        .select_related('categoria', 'autor')
        .order_by('-destacada', '-fecha_publicacion')
    )

    categoria_slug = request.GET.get('cat', '').strip()
    if categoria_slug:
        qs = qs.filter(categoria__slug=categoria_slug)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(titulo__icontains=q) |
            Q(extracto__icontains=q) |
            Q(contenido__icontains=q)
        )

    paginator = Paginator(qs, 9)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    categorias = Categoria.objects.filter(activa=True).order_by('orden', 'nombre')

    contexto = {
        'page_obj': page_obj,
        'noticias': page_obj,
        'categorias': categorias,
        'categoria_actual': categoria_slug,
        'busqueda': q,
        'total': paginator.count,
    }
    return render(request, 'noticias/lista.html', contexto)


def detalle_noticia(request, slug):
    """Detalle público de una noticia."""
    ahora = timezone.now()
    noticia = get_object_or_404(
        Noticia.objects.select_related('categoria', 'autor'),
        slug=slug,
        estado='publicada',
    )

    if not noticia.esta_publicada:
        messages.warning(request, "Esta noticia no está disponible.")
        return redirect('noticias:lista')

    noticia.incrementar_vista()
    noticia.refresh_from_db()

    relacionadas = Noticia.objects.none()
    if noticia.categoria:
        relacionadas = (
            Noticia.objects
            .filter(
                estado='publicada',
                fecha_publicacion__lte=ahora,
                categoria=noticia.categoria,
            )
            .filter(Q(fecha_expiracion__isnull=True) | Q(fecha_expiracion__gte=ahora))
            .exclude(pk=noticia.pk)
            .select_related('categoria')
            .order_by('-fecha_publicacion')[:3]
        )

    contexto = {
        'noticia': noticia,
        'relacionadas': relacionadas,
    }
    return render(request, 'noticias/detalle.html', contexto)


# ============================================================
# VISTAS ADMIN
# ============================================================

@staff_member_required
def admin_lista(request):
    """Lista de noticias en el panel admin."""
    qs = (
        Noticia.objects
        .select_related('categoria', 'autor')
        .order_by('-fecha_creacion')
    )

    estado = request.GET.get('estado', '').strip()
    categoria_id = request.GET.get('cat', '').strip()
    q = request.GET.get('q', '').strip()

    if estado:
        qs = qs.filter(estado=estado)
    if categoria_id:
        qs = qs.filter(categoria_id=categoria_id)
    if q:
        qs = qs.filter(Q(titulo__icontains=q) | Q(extracto__icontains=q))

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    categorias = Categoria.objects.all().order_by('orden', 'nombre')

    contexto = {
        'page_obj': page_obj,
        'noticias': page_obj,
        'categorias': categorias,
        'filtros': {
            'estado': estado,
            'cat': categoria_id,
            'q': q,
        },
        'total': paginator.count,
        'estados': Noticia.ESTADOS,
    }
    return render(request, 'noticias/admin/lista.html', contexto)


@staff_member_required
def admin_crear(request):
    """Crear nueva noticia."""
    if request.method == 'POST':
        form = NoticiaForm(request.POST, request.FILES)
        if form.is_valid():
            noticia = form.save(commit=False)
            noticia.autor = request.user
            noticia.save()

            # Guardar imágenes de galería
            imagenes = request.FILES.getlist('imagenes_galeria')
            for i, img in enumerate(imagenes):
                ImagenNoticia.objects.create(
                    noticia=noticia,
                    imagen=img,
                    orden=i,
                )

            messages.success(
                request,
                f"Noticia «{noticia.titulo}» creada con {len(imagenes)} imagen(es) adicional(es)."
            )
            return redirect('noticias:admin_lista')
    else:
        form = NoticiaForm()

    contexto = {
        'form': form,
        'accion': 'crear',
        'noticia': None,
    }
    return render(request, 'noticias/admin/formulario.html', contexto)


@staff_member_required
def admin_editar(request, noticia_id):
    """Editar noticia existente."""
    noticia = get_object_or_404(Noticia, id=noticia_id)

    if request.method == 'POST':
        form = NoticiaForm(request.POST, request.FILES, instance=noticia)
        if form.is_valid():
            noticia = form.save()

            # Guardar imágenes nuevas de galería
            imagenes = request.FILES.getlist('imagenes_galeria')
            orden_actual = noticia.imagenes_galeria.count()
            for i, img in enumerate(imagenes):
                ImagenNoticia.objects.create(
                    noticia=noticia,
                    imagen=img,
                    orden=orden_actual + i,
                )

            messages.success(request, f"Noticia «{noticia.titulo}» actualizada.")
            return redirect('noticias:admin_lista')
    else:
        form = NoticiaForm(instance=noticia)

    contexto = {
        'form': form,
        'accion': 'editar',
        'noticia': noticia,
    }
    return render(request, 'noticias/admin/formulario.html', contexto)


@staff_member_required
def admin_eliminar(request, noticia_id):
    """Confirmar y eliminar noticia."""
    noticia = get_object_or_404(Noticia, id=noticia_id)

    if request.method == 'POST':
        titulo = noticia.titulo
        noticia.delete()
        messages.warning(request, f"Noticia «{titulo}» eliminada.")
        return redirect('noticias:admin_lista')

    return render(request, 'noticias/admin/confirmar_eliminar.html', {'noticia': noticia})


@staff_member_required
def admin_toggle_destacada(request, noticia_id):
    """Alternar el estado destacado de una noticia."""
    if request.method != 'POST':
        return redirect('noticias:admin_lista')

    noticia = get_object_or_404(Noticia, id=noticia_id)
    noticia.destacada = not noticia.destacada
    noticia.save(update_fields=['destacada'])
    messages.info(
        request,
        f"Noticia «{noticia.titulo}» {'destacada' if noticia.destacada else 'no destacada'}."
    )
    return redirect('noticias:admin_lista')


@staff_member_required
def admin_eliminar_imagen(request, imagen_id):
    """Elimina una imagen de galería (AJAX)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    imagen = get_object_or_404(ImagenNoticia, id=imagen_id)
    imagen.delete()
    return JsonResponse({'ok': True})


# ============================================================
# CATEGORÍAS (ADMIN)
# ============================================================

@staff_member_required
def admin_categorias(request):
    """Gestión de categorías."""
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría creada correctamente.")
            return redirect('noticias:admin_categorias')
    else:
        form = CategoriaForm()

    categorias = Categoria.objects.all().order_by('orden', 'nombre')

    contexto = {
        'form': form,
        'categorias': categorias,
    }
    return render(request, 'noticias/admin/categorias.html', contexto)


@staff_member_required
def admin_categoria_eliminar(request, categoria_id):
    """Eliminar categoría (solo POST)."""
    if request.method != 'POST':
        return redirect('noticias:admin_categorias')

    categoria = get_object_or_404(Categoria, id=categoria_id)
    nombre = categoria.nombre
    categoria.delete()
    messages.warning(request, f"Categoría «{nombre}» eliminada.")
    return redirect('noticias:admin_categorias')