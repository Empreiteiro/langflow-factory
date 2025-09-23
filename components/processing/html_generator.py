from lfx.custom import Component
from lfx.io import MultilineInput, MessageTextInput, Output
from lfx.schema.message import Message


class HTMLTextInputComponent(Component):
    display_name = "HTML Generator"
    description = "Injects individual user inputs into an HTML template. Add input fields for each data field you want to inject."
    icon = "code"
    name = "HTMLTextInput"

    inputs = [
        MultilineInput(
            name="templateHtml",
            display_name="HTML Template",
            info="HTML template with placeholders like {nome}, {documento}, etc. Add input fields for each data field you want to inject into the template.",
        ),
        MessageTextInput(
            name="nome", 
            display_name="Name", 
            tool_mode=True
        ),
        MessageTextInput(
            name="documento", 
            display_name="Document", 
            tool_mode=True
            ),
        MessageTextInput(
            name="data_emissao", 
            display_name="Issue Date", 
            tool_mode=True),
        MultilineInput(
            name="tabela_titulos", 
            display_name="Table Titles (HTML)", 
            tool_mode=True),
    ]

    outputs = [
        Output(display_name="Message", name="output", method="html_generator"),
    ]

    def html_generator(self) -> Message:
        try:
            html_output = self.templateHtml.format(
                nome=self.nome,
                documento=self.documento,
                data_emissao=self.data_emissao,
                tabela_titulos=self.tabela_titulos,
            )
            self.status = "HTML generated successfully."
            return Message(text=html_output)
        except Exception as e:
            self.status = f"Error generating HTML: {e}"
            return Message(text=f"Error: {e}")
