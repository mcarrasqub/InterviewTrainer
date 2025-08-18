# InterviewTrainer (Lumo)

Instrucciones para configurar y ejecutar el proyecto InterviewTrainer.

## 1. Clonar el repositorio

Abre tu terminal (por ejemplo, en VS Code) y ejecuta:

```bash
git clone https://github.com/mcarrasqub/InterviewTrainer.git
cd InterviewTrainer
```

## 2. Preparar entorno virtual (lumo_env)
Para crear y activar un entorno virtual llamado `lumo_env`, ejecuta en la terminal:

### macOS / Linux:
```bash
python3 -m venv lumo_env
source lumo_env/bin/activate
```

### Windows (PowerShell):
```powershell
python -m venv lumo_env
.\lumo_env\Scripts\Activate.ps1
```

### Windows (CMD):
```cmd
python -m venv lumo_env
.\lumo_env\Scripts\activate.bat
```

Una vez activado, el prompt de tu terminal debería cambiar y mostrar algo como `(lumo_env)` al inicio.

## 3. Instalar dependencias

Con el entorno activado, instala las dependencias listadas en `requirements.txt`:

```bash
pip install -r requirements.txt
```

Esto asegura que todas las bibliotecas necesarias estén instaladas.


## 4. Ejecutar el proyecto

Dependiendo de cómo esté diseñado, podrías usar alguno de los siguientes comandos:

### Si hay un script de arranque:

**Windows (CMD o PowerShell):**
```cmd
run.bat
```

**macOS / Linux:**
```bash
./setup.sh
```

### Si se trata de una app Django:

```bash
python manage.py runserver
```

Esto levantará el servidor local, normalmente accesible en [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## Notas adicionales

- Asegúrate de tener Python instalado en tu sistema
- Si encuentras problemas con permisos en macOS/Linux, es posible que necesites hacer ejecutable el script: `chmod +x setup.sh`
- Para desactivar el entorno virtual cuando termines, simplemente ejecuta `deactivate` en la terminal
