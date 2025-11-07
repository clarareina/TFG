from flow import run_agent

if __name__ == "__main__":
    print("Escribe una instrucción (o 'salir' para terminar):\n")

    while True:
        user_input = input("> ").strip()
        if not user_input:
            continue
        if user_input.lower() in ["salir", "exit", "quit"]:
            print("Finalizando agente.")
            break

        result = run_agent(user_input)
        print(result)

