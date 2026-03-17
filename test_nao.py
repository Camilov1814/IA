"""
test_nao.py - Prueba de conexion y voz con NAO via SSH.

El puerto 9559 usa protocolo binario qi (no HTTP).
La solucion para Windows Python 3 es SSH: conectarse al robot
y ejecutar los comandos usando su propio Python + naoqi interno.

Dependencia:
    pip install paramiko
"""

import os
import socket
import paramiko

NAO_IP       = "172.16.18.25"
NAO_USER     = "nao"
NAO_PASSWORD = "nao"          # Contrasena por defecto del NAO


# ─── PASO 1: Verificar conectividad de red ────────────────────────────────────
def test_puerto(ip, port, nombre):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    ok = sock.connect_ex((ip, port)) == 0
    sock.close()
    estado = "[OK]   " if ok else "[FALLO]"
    print(f"  {estado} Puerto {port} ({nombre})")
    return ok


# ─── PASO 2: Conectar por SSH y hablar ───────────────────────────────────────
def nao_celebrate_ssh(ip, user, password):
    """
    1. Sube dance-moves.mp3 al robot via SFTP.
    2. NAO habla, reproduce el audio desde sus propios altavoces
       y ejecuta la animacion de celebracion al mismo tiempo.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mp3_local  = os.path.join(script_dir, "dance-moves.mp3")
    mp3_remoto = "/home/nao/dance-moves.mp3"

    # Comando en el robot:
    # ap.post.playFile -> no bloqueante (audio corre en paralelo)
    # bm.runBehavior   -> bloqueante (espera que termine el baile)
    cmd = (
        "python -c \""
        "import naoqi; "
        "tts = naoqi.ALProxy('ALTextToSpeech', '127.0.0.1', 9559); "
        "ap  = naoqi.ALProxy('ALAudioPlayer',  '127.0.0.1', 9559); "
        "bm  = naoqi.ALProxy('ALBehaviorManager', '127.0.0.1', 9559); "
        "tts.setLanguage('Spanish'); "
        "tts.say('Gane.'); "
        "ap.post.playFile('/home/nao/dance-moves.mp3'); "
        "bm.runBehavior('animations/Stand/Gestures/Enthusiastic_5')"
        "\""
    )
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=user, password=password, timeout=5,
                    allow_agent=False, look_for_keys=False)

        # Subir el mp3 al robot
        if os.path.exists(mp3_local):
            sftp = ssh.open_sftp()
            sftp.put(mp3_local, mp3_remoto)
            sftp.close()
            print(f"  [OK]  dance-moves.mp3 subido al robot.")
        else:
            print(f"  [WARN] No se encontro {mp3_local}, solo se ejecutara el baile.")

        _, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()
        errores = stderr.read().decode().strip()
        ssh.close()
        if errores:
            print(f"  [WARN] Stderr: {errores}")
        else:
            print(f"  [OK]  Celebracion completada.")
        return True
    except Exception as e:
        print(f"  [FALLO] Error en celebracion: {e}")
        return False


def nao_say_ssh(ip, user, password, text):
    """
    Se conecta al robot por SSH y ejecuta ALTextToSpeech.say
    usando el Python 2.7 y naoqi que el propio NAO tiene instalados.
    """
    cmd = (
        f"python -c \""
        f"import naoqi; "
        f"tts = naoqi.ALProxy('ALTextToSpeech', '127.0.0.1', 9559); "
        f"tts.setLanguage('Spanish'); "
        f"tts.say('{text}')"
        f"\""
    )
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=user, password=password, timeout=5,
                        allow_agent=False, look_for_keys=False)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()  # Esperar a que termine
        errores = stderr.read().decode().strip()
        ssh.close()
        if errores:
            print(f"  [WARN] Stderr: {errores}")
        else:
            print(f"  [OK]  NAO dijo: '{text}'")
        return True
    except paramiko.AuthenticationException:
        print(f"  [FALLO] Autenticacion fallida. Verifica usuario/contrasena.")
        return False
    except Exception as e:
        print(f"  [FALLO] Error SSH: {e}")
        return False


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 52)
    print(f"  Test de conexion NAO  ->  {NAO_IP}")
    print("=" * 52)

    print("\n[1] Verificando puertos de red...")
    sdk_ok = test_puerto(NAO_IP, 9559, "NAOqi SDK")
    ssh_ok = test_puerto(NAO_IP, 22,   "SSH")

    print("\n[2] Probando texto a voz via SSH...")
    if ssh_ok:
        nao_say_ssh(NAO_IP, NAO_USER, NAO_PASSWORD,
                    "Hola, Sebas es una locota")
    else:
        print("  [SKIP] SSH no disponible.")

    print("\n[3] Probando celebracion (baile + audio desde altavoces de NAO)...")
    if ssh_ok:
        # nao_celebrate_ssh sube el mp3 y lo reproduce desde el robot
        nao_celebrate_ssh(NAO_IP, NAO_USER, NAO_PASSWORD)
    else:
        print("  [SKIP] SSH no disponible.")

    print("\n" + "=" * 52)
    if ssh_ok:
        print("  Conexion SSH OK. El juego puede comunicarse con NAO.")
    else:
        print("  No se pudo conectar por SSH.")
        print(f"  Verifica que el robot este encendido en {NAO_IP}")
    print("=" * 52)
