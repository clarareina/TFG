from app.flow import run_agent

if __name__ == "__main__":
    print("Escribe una instrucción (o 'salir' para terminar):")

    while True:
        user_input = input("> ").strip()
        if not user_input:
            continue
        if user_input.lower() in ["salir", "exit", "quit"]:
            print("Finalizando agente.")
            break

        result = run_agent(user_input)
