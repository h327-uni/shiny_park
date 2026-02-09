from shiny import App, render, ui

app_ui = ui.page_fluid(
    ui.h2("Hello Shiny!"),
    ui.input_slider("n", "Sample Size", min=10, max=500, value=100),
    ui.output_text_verbatim("txt"),
)

def server(input, output, session):
    @output
    @render.text
    def txt():
        return f"You selected n = {input.n()}"

app = App(app_ui, server)