# render, redirect, get_object_or_404: los mismos atajos de Django que ya usabas en la Semana 5
from django.shortcuts import render, redirect, get_object_or_404
# connection: datos de la conexión a la base (lo usa la vista "inicio" de la Semana 3)
from django.db import connection
# login_required: decorador que exige sesión iniciada antes de entrar a la vista
from django.contrib.auth.decorators import login_required
# login: inicia la sesión de un usuario · logout: la cierra
from django.contrib.auth import login, logout
# UserCreationForm: formulario de registro listo · AuthenticationForm: formulario de inicio de sesión listo
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
# messages: mensajes flash que se muestran una sola vez y luego desaparecen
from django.contrib import messages
# Paginator: divide una lista larga de registros en páginas de tamaño fijo
from django.core.paginator import Paginator
# Servicio: el modelo de la Semana 4
from .models import Servicio
# ServicioForm: el ModelForm de la Semana 5
from .forms import ServicioForm


# inicio: la vista de la Semana 3 que muestra a qué base estás conectado (no cambia)
def inicio(request):
    # settings_dict: diccionario con ENGINE, HOST, NAME, etc. de la conexión activa
    info_bd = connection.settings_dict
    # contexto: los datos que la plantilla podrá usar
    contexto = {
        # motor: el tipo de base de datos (debe decir mysql)
        'motor': info_bd['ENGINE'],
        # host: el servidor de la base (en Aiven termina en aivencloud.com)
        'host': info_bd['HOST'],
    # cierre del diccionario contexto
    }
    # render: junta inicio.html con el contexto y devuelve la página
    return render(request, 'core/inicio.html', contexto)


# @login_required: si no hay sesión, manda a LOGIN_URL en lugar de ejecutar la vista
@login_required
# servicios: la vista del listado, ahora con búsqueda y paginación
def servicios(request):
    # filter(propietario=request.user): solo los servicios del usuario actual (Semana 6)
    # order_by('-creado_en', '-id'): del más nuevo al más viejo; '-id' desempata si dos se crearon al mismo tiempo (paginar exige un orden fijo)
    lista_servicios = Servicio.objects.filter(propietario=request.user).order_by('-creado_en', '-id')
    # request.GET.get('q', ''): lee el texto buscado desde ?q=algo; '' si no hay búsqueda · strip() quita espacios sobrantes
    query = request.GET.get('q', '').strip()
    # si el usuario escribió algo en el buscador...
    if query:
        # titulo__icontains=query: WHERE titulo LIKE '%query%', sin distinguir mayúsculas/minúsculas
        lista_servicios = lista_servicios.filter(titulo__icontains=query)
    # Paginator(lista, 5): agrupa los resultados (ya filtrados) en páginas de 5 registros cada una
    paginator = Paginator(lista_servicios, 5)
    # request.GET.get('page'): lee el número de página desde la URL, ej. ?page=2
    numero_pagina = request.GET.get('page')
    # get_page(): devuelve la página pedida; si no es un número da la 1, y si se pasa del total da la última
    pagina = paginator.get_page(numero_pagina)
    # servicios: la página actual (se recorre igual que una lista) · query: para que el buscador recuerde lo escrito
    return render(request, 'core/servicios.html', {'servicios': pagina, 'query': query})


# @login_required: si nadie inició sesión, Django lo manda a LOGIN_URL (el login de /admin)
@login_required
# crear_servicio: la vista que atiende /servicios/nuevo/
def crear_servicio(request):
    # request.method: distingue si el navegador pide el formulario (GET) o lo está enviando (POST)
    if request.method == 'POST':
        # ServicioForm(request.POST): reconstruye el formulario con los datos que el usuario tecleó
        form = ServicioForm(request.POST)
        # is_valid(): corre todas las validaciones del modelo (tipos, max_length, campos obligatorios)
        if form.is_valid():
            # commit=False: crea el objeto Servicio en memoria SIN guardarlo todavía en MySQL
            nuevo = form.save(commit=False)
            # propietario: se asigna aquí, no en el formulario, para que nadie pueda falsificarlo
            nuevo.propietario = request.user
            # save(): ahora sí guarda el registro completo en MySQL
            nuevo.save()
            # redirect('servicios'): evita reenvíos duplicados si el usuario recarga la página
            return redirect('servicios')
    # si no es POST, es GET: el usuario apenas abrió la página
    else:
        # ServicioForm() sin datos: formulario vacío
        form = ServicioForm()
    # render: dibuja la plantilla, pasándole el formulario (vacío o con errores)
    return render(request, 'core/servicio_form.html', {'form': form, 'titulo_pagina': 'Nuevo servicio'})


# @login_required: solo usuarios con sesión pueden editar
@login_required
# pk: el id que viene en la URL /servicios/<pk>/editar/
def editar_servicio(request, pk):
    # get_object_or_404 con DOS condiciones: el id correcto Y que el dueño sea el usuario actual
    # si alguien intenta editar el servicio de otro cambiando el número en la URL, recibe un 404
    servicio = get_object_or_404(Servicio, pk=pk, propietario=request.user)
    # si el usuario envió el formulario con cambios, la petición llega como POST
    if request.method == 'POST':
        # instance=servicio: el formulario actualiza ESE registro en vez de crear uno nuevo
        form = ServicioForm(request.POST, instance=servicio)
        # is_valid(): revisa tipos, campos obligatorios y tu clean_precio
        if form.is_valid():
            # save(): guarda los cambios en MySQL (UPDATE)
            form.save()
            # redirect: regresa al listado después de guardar
            return redirect('servicios')
    # si no es POST, es GET: se acaba de abrir la pantalla de edición
    else:
        # formulario precargado con los datos actuales del servicio
        form = ServicioForm(instance=servicio)
    # render: dibuja el mismo template de Crear, con título "Editar servicio"
    return render(request, 'core/servicio_form.html', {'form': form, 'titulo_pagina': 'Editar servicio'})


# @login_required: solo usuarios con sesión iniciada pueden borrar
@login_required
# eliminar_servicio: recibe el pk (id) desde la URL /servicios/<pk>/eliminar/
def eliminar_servicio(request, pk):
    # mismo candado que en editar: el id correcto Y que el dueño sea el usuario actual; si no, 404
    servicio = get_object_or_404(Servicio, pk=pk, propietario=request.user)
    # solo se borra si llega un POST (el botón de confirmar), nunca con un simple GET
    if request.method == 'POST':
        # delete(): borra la fila de MySQL de verdad
        servicio.delete()
        # redirect: regresa al listado, ya sin el registro borrado
        return redirect('servicios')
    # si es GET, solo muestra la pantalla de "¿Seguro?"; todavía no borra nada
    return render(request, 'core/servicio_confirm_delete.html', {'servicio': servicio})


# registro: la vista que atiende /registro/ (recibe la petición del navegador)
def registro(request):
    # si el usuario envió el formulario (botón «Registrarme»), la petición llega como POST
    if request.method == 'POST':
        # reconstruye el formulario con los datos tecleados (usuario y contraseñas)
        form = UserCreationForm(request.POST)
        # is_valid(): revisa que el usuario no exista y que las 2 contraseñas coincidan y sean seguras
        if form.is_valid():
            # save(): crea el User en MySQL, ya con la contraseña hasheada por Django
            usuario_nuevo = form.save()
            # login(): inicia sesión automáticamente con la cuenta recién creada
            login(request, usuario_nuevo)
            # messages.success: mensaje verde de bienvenida que se verá una sola vez en la siguiente página
            messages.success(request, f'Cuenta creada. ¡Bienvenido, {usuario_nuevo.username}!')
            # redirect: manda al usuario ya logueado al listado (name='servicios')
            return redirect('servicios')
    # si no es POST, es GET: el usuario apenas abrió la página
    else:
        # formulario vacío para cuando la vista se abre por primera vez (GET)
        form = UserCreationForm()
    # render: dibuja registro.html con el formulario (vacío o con los errores)
    return render(request, 'core/registro.html', {'form': form})


# iniciar_sesion: la vista que atiende /login/
def iniciar_sesion(request):
    # si el usuario envió usuario y contraseña, la petición llega como POST
    if request.method == 'POST':
        # AuthenticationForm necesita "request" además de los datos, para poder validar contra la BD
        form = AuthenticationForm(request, data=request.POST)
        # is_valid(): aquí Django comprueba que el usuario exista y la contraseña sea correcta
        if form.is_valid():
            # get_user(): devuelve el User ya verificado · login(): guarda la sesión en una cookie
            login(request, form.get_user())
            # messages.success: mensaje verde que confirma el inicio de sesión
            messages.success(request, 'Sesión iniciada correctamente.')
            # redirect: tras iniciar sesión, lo manda al listado de servicios
            return redirect('servicios')
    # si no es POST, es GET: el usuario apenas abrió la página de login
    else:
        # AuthenticationForm(): formulario vacío de usuario y contraseña
        form = AuthenticationForm()
    # render: dibuja login.html con el formulario (vacío o con el error de credenciales)
    return render(request, 'core/login.html', {'form': form})


# cerrar_sesion: la vista que atiende /logout/
def cerrar_sesion(request):
    # logout(request): invalida la sesión actual; request.user vuelve a ser AnonymousUser
    logout(request)
    # messages.info: guarda un mensaje que se muestra una única vez en la próxima página
    messages.info(request, 'Sesión cerrada correctamente.')
    # redirect: manda a la pantalla de login, donde se verá el mensaje
    return redirect('login')