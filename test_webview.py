import webview

class Api:
    def hello(self, name):
        return f"¡Hola {name} desde Python!"

def main():
    api = Api()
    # Create webview window loading local HTML
    window = webview.create_window(
        title="POS Web Prueba",
        html="""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Test POS</title>
            <style>
                body {
                    background-color: #18181b;
                    color: #f4f4f5;
                    font-family: system-ui, sans-serif;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                }
                button {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    font-size: 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    margin-top: 20px;
                    transition: background-color 0.2s;
                }
                button:hover {
                    background-color: #106ebe;
                }
                #result {
                    margin-top: 20px;
                    font-size: 18px;
                    color: #10b981;
                }
            </style>
        </head>
        <body>
            <h1>Prueba de Frontend Web (PyWebView)</h1>
            <p>Presiona el botón para llamar a una función en Python de forma asíncrona:</p>
            <button onclick="callPython()">Saludar a Python</button>
            <div id="result"></div>

            <script>
                function callPython() {
                    if (window.pywebview && window.pywebview.api) {
                        window.pywebview.api.hello("Cajero/Admin").then(function(response) {
                            document.getElementById("result").innerText = response;
                        });
                    } else {
                        document.getElementById("result").innerText = "Error: pywebview api no está lista.";
                    }
                }
            </script>
        </body>
        </html>
        """,
        js_api=api,
        width=800,
        height=600,
    )
    webview.start()

if __name__ == '__main__':
    main()
