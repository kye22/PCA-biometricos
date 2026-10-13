Práctica Sistemas Biométricos

La práctica de la asignatura Sistemas Biométricos tiene como objetivo la creación y evaluación de
un sistema de reconocimiento facial. La práctica se realiza en grupos y cada grupo debe aplicar una
aproximación   al   reconocimiento   facial   distinta   (repartidas   las   opciones   entre   los   grupos).   La
práctica consta de cuatro fases principales:

• Creación del sistema de reconocimiento facial.
• Evaluación del sistema de reconocimiento facial.
• Evaluación del sistema de reconocimiento facial de un grupo "rival".
• Exposición de resultados/conclusiones.

De cara a que el intercambio de sistemas entre grupos sea lo más fácil posible, se imponen las
siguientes restricciones:

• Las práctica se realizará en lenguaje Python.
•

Se preparará un repositorio que facilite al máximo la ejecución del sistema. A poder ser,
incluyendo un docker listo para su uso.
• La base de datos del sistema será un .csv.
• El sistema debe tener inscritos a 51 personas conocidas. Las fotos de 50 de esas personas las
proporcionará el docente y serán comunes para todos los equipos. La última es elección de
cada equipo.

• El sistema tiene que tener los siguientes métodos:

◦ inscribir(id, foto): método para inscribir a una persona a partir de su nombre y una foto.
◦ verificar(id, foto): método para verificar a una persona a partir de su nombre y una foto.
◦ identificar(foto): método para identificar a una persona a partir de una foto.
◦ inscribir_sd(id, foto): método para inscribir a una persona a partir de su nombre y una

foto omitiendo el detector de caras.

◦ verificar_sd(id, foto): método para verificar a una persona a partir de su nombre y una

foto omitiendo el detector de caras.

◦ identificar_sd(foto): método para identificar a una persona a partir de una foto omitiendo

el detector de caras.

◦ inscribir_t(id, template): método para inscribir a una persona a partir de su nombre y un

template omitiendo el detector de caras y el extractor de características.

◦ verificar_t(id, template): método para verificar a una persona a partir de su nombre y una

foto omitiendo el detector de caras y el extractor de características.

◦ identificar_t(template):   método   para   identificar   a   una   persona   a   partir   de   una   foto

omitiendo el detector de caras y el extractor de características.

Queda   a   criterio   de   cara   equipo   cómo   evalúa   su   propio   sistema   y   el   del   "rival",   pero   en   esas
evaluaciones tendrán que incluirse los supuestos de que el sistema ha sido atacado y el atacante se
salta alguna parte del sistema, consigue leer la base de datos o incluso consigue escribir en la base
de datos.

El objetivo no es crear un sistema sin defectos (eso es imposible). El objetivo es que el grupo
"rival" no encuentre defectos desconocidos para el grupo.

