"""
最小化 Gradio 测试 - 验证安装
"""
import gradio as gr

def greet(name):
    return f"你好 {name}! Gradio 工作正常！"

with gr.Blocks(title="Gradio测试") as demo:
    gr.Markdown("# 🎯 Gradio 安装测试")
    
    with gr.Row():
        name_input = gr.Textbox(label="输入你的名字", value="用户")
        output = gr.Textbox(label="输出结果")
    
    btn = gr.Button("测试", variant="primary")
    btn.click(fn=greet, inputs=[name_input], outputs=[output])

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7862,
        share=False
    )
