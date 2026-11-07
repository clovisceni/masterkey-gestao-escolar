@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m pip install -r requirements.txt
  if errorlevel 1 goto erro
  py -3 app.py
) else (
  python -m pip install -r requirements.txt
  if errorlevel 1 goto erro
  python app.py
)
goto fim
:erro
echo Nao foi possivel instalar as dependencias. Confira a conexao com a internet e tente novamente.
:fim
pause
