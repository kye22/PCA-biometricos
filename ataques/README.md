# Red team propio: hipótesis y evidencias

Antes de probar ataques, monta el sistema. Los scripts no alteran la BD original.

| Escenario del enunciado | Script | Qué comprobar |
|---|---|---|
| Lectura de `bd.csv` sin clave | `python ataques/lectura_bd.py` | Los ids son visibles; el campo de template es un texto cifrado, no un vector utilizable. |
| Escritura no autorizada en el CSV | `python ataques/escritura_bd.py --modo alterar` | HMAC detecta la modificación de la copia. |
| Borrado completo de BD y firma | `python ataques/escritura_bd.py --modo borrar-todo` | **Limitación de disponibilidad:** si faltan ambos archivos, `bd.cargar()` devuelve BD vacía. |
| Saltarse detector / extractor | `python ataques/bypass.py ID FOTO` | Contrastar API completa, `_sd` (recorte) y `_t` (vector real). |

## Alcance de las defensas

- Se supone que el atacante puede leer o escribir **la BD**, pero no dispone de la **clave**. Si
  obtiene también `datos/clave.key`, la confidencialidad y las firmas dejan de proteger frente a él.
- Los métodos `inscribir_*` no exigen autenticación de administrador. Si el rival obtiene acceso
  autorizado a esos métodos, puede añadir templates legítimamente; HMAC no lo previene.
- `verificar_sd` e `identificar_sd` evitan el detector de la cadena principal pero ejecutan
  `detector.parece_cara` con YuNet como defensa secundaria heredada. **Puede contradecir la
  lectura literal del enunciado**, y debe discutirse en la evaluación. No se ha modificado.
- Las distancias y el ranking expuestos por la interfaz web pueden ayudar a un atacante que
  haga muchas consultas; el límite local por IP es una mitigación parcial.
- Los scripts son demostraciones controladas, no una garantía de seguridad general.

Registra cada prueba en el informe con: capacidad del atacante, entrada, resultado esperado,
resultado observado, defensa activada y debilidad residual. Evita atribuir un éxito o fallo a una
prueba que no hayas ejecutado.
