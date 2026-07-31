@echo off
echo Instalando Sistema...

REM Crear carpeta y copiar archivos
mkdir "C:\SistemaPOS"
xcopy ".\dist\main\*" "C:\SistemaPOS\" /E /I /Y
copy ".\dist\backup_db.exe" "C:\SistemaPOS\" /Y

REM Programar backup automatico a las 21:00 hs
schtasks /create /tn "Backup_Sistema_POS" /tr "C:\SistemaPOS\backup_db.exe" /sc daily /st 21:00 /rl highest /f

echo Instalacion finalizada con exito.
pause