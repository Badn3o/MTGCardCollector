# Migración de módulo BadBunny

Se retiró el módulo `BadBunny/` de este repositorio porque debe vivir en:

- https://github.com/Badn3o/BadBunny

## Estado en este entorno

La migración automática no se pudo completar desde aquí por restricción de red/proxy a GitHub (`CONNECT tunnel failed, response 403`).

## Pasos recomendados para completar la migración desde una máquina con acceso

```bash
# 1) Clonar ambos repos

git clone https://github.com/Badn3o/MTGCardCollector.git
cd MTGCardCollector

git clone https://github.com/Badn3o/BadBunny.git ../BadBunny

# 2) Copiar el contenido histórico del módulo (desde commit anterior)

git checkout HEAD~1 -- BadBunny
rsync -av BadBunny/ ../BadBunny/

# 3) Commit y push en repo destino
cd ../BadBunny
git add .
git commit -m "feat: importar bot de Telegram y monitor TicketSwap"
git push origin main
```

## Resultado esperado

- `MTGCardCollector` queda sin el directorio `BadBunny/`.
- `BadBunny` pasa a contener el bot de Telegram y el monitor de TicketSwap.
