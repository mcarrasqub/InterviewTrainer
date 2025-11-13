# InterviewTrainer (Lumo)

Instructions to set up and run the InterviewTrainer project.

## 1. Clone the repository

Open your terminal (e.g., in VS Code) and run:

```bash
git clone https://github.com/mcarrasqub/InterviewTrainer.git
cd InterviewTrainer
```

## 2. Set up virtual environment (lumo_env)

To create and activate a virtual environment named `lumo_env`, run in the terminal:

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

Once activated, your terminal prompt should change and show something like `(lumo_env)` at the beginning.

## 3. Install dependencies

With the environment activated, install the dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

This ensures that all necessary libraries are installed.

Create your APIkey on aistudio.google.com and paste it in a new file called .env:
/.env: 
SECRET_KEY=tu-clave-secreta-super-segura-aqui
DEBUG=True
GEMINI_API_KEY= (insert APIkey)


## 4. Make migrations

 Use this commands for make migrations of the database:
 
 ```bash
python manage.py makemigrations
python manage.py migrate
```


## 5. Run the project

Depending on how it's designed, you could use any of the following commands:

### If there's a startup script:

**Windows (CMD or PowerShell):**
```cmd
run.bat
```

**macOS / Linux:**
```bash
./setup.sh
```

### If it's a Django app:

```bash
python manage.py runserver
```

This will start the local server, usually accessible at [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## Additional notes

- Make sure you have Python installed on your system
- To deactivate the virtual environment when you're done, simply run `deactivate` in the terminal
