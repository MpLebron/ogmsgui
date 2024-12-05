import json
import os
import ipywidgets as widgets
from ipyfilechooser import FileChooser
from IPython.display import display
from IPython.display import Javascript

# 
class Model:
    """模型基类,用于处理模型的基本属性和操作"""
    def __init__(self, model_data):
        mdl_json = model_data.get("mdlJson", {})
        mdl = mdl_json.get("mdl", {})
        
        self.id = model_data.get("_id", "")
        self.name = mdl.get("name", "未命名模型")
        self.description = model_data.get("description", "")
        self.author = model_data.get("author", "")
        self.tags = model_data.get("normalTags", [])
        self.tags_en = model_data.get("normalTagsEn", [])
        
        # 直接使用原始的states数据
        self.states = mdl.get("states", [])

class ModelGUI:
    """模型GUI类,负责创建和管理GUI界面"""
    def __init__(self):
        self.models = {}  # 存储所有加载的模型
        self.current_model = None  # 当前选中的模型
        self.widgets = {}  # 存储GUI组件
        
        # 在初始化时直接加载模型���
        self._load_models()
    
    def _load_models(self):
        """加载模型配置文件"""
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建JSON文件路径
        json_path = os.path.join(current_dir, "data", "computeModel.json")
        
        try:
            with open(json_path, encoding='utf-8') as f:
                models_data = json.load(f)
                for model_name, model_data in models_data.items():
                    self.models[model_name] = Model(model_data)
        except Exception as e:
            print(f"加载模型配置文件失败: {str(e)}")
            self.models = {}  # 确保models是空字典而不是None
    
    def create_gui(self):
        """创建主GUI界面"""
        main_widget = widgets.VBox()
        
        # 创建模型选择下拉框
        self.widgets['model_selector'] = widgets.Dropdown(
            options=list(self.models.keys()),
            description='选择模型:',
            style={'description_width': 'initial'}
        )
        self.widgets['model_selector'].observe(self._on_model_selected, 'value')
        
        # 创建模型信息显示区
        self.widgets['model_info'] = widgets.HTML()
        
        # 创建参数输入区
        self.widgets['params_area'] = widgets.VBox()
        
        # 创建运行按钮
        self.widgets['run_button'] = widgets.Button(description='运行模型')
        self.widgets['run_button'].on_click(self._on_run_clicked)
        
        # 创建输出区
        self.widgets['output_area'] = widgets.Output()
        
        main_widget.children = [
            self.widgets['model_selector'],
            self.widgets['model_info'],
            self.widgets['params_area'],
            self.widgets['run_button'],
            self.widgets['output_area']
        ]
        
        return main_widget
    
    def _on_model_selected(self, change):
        """处理模型选择事件"""
        if change['new']:
            self.current_model = self.models[change['new']]
            self._update_model_info()
            self._create_param_widgets()
    
    def _update_model_info(self):
        """更新模型信息显示"""
        info_html = f"""
        <h3>{self.current_model.name}</h3>
        <p><b>描述:</b> {self.current_model.description}</p>
        <p><b>作者:</b> {self.current_model.author}</p>
        <p><b>标签:</b> {', '.join(self.current_model.tags)}</p>
        """
        self.widgets['model_info'].value = info_html
    
    def _create_param_widgets(self):
        """创建参数入组件"""
        param_widgets = []
        for data_name, data_info in self.current_model.data_items.items():
            if data_info['type'] == 'internal':
                widget = FileChooser(
                    title=f"{data_name}: {data_info['description']}"
                )
                self.widgets[f'param_{data_name}'] = widget
                param_widgets.append(widget)
        
        self.widgets['params_area'].children = param_widgets
    
    def _on_run_clicked(self, b):
        """处理运行按钮点击事件"""
        with self.widgets['output_area']:
            self.widgets['output_area'].clear_output()
            print(f"运行模型: {self.current_model.name}")
            # 这里添加实际的模型运行代码
            
    def show(self):
        """显示GUI界面"""
        return self.create_gui()
    
    def show_model(self, model_name):
        """显示指定模型的GUI界面"""
        if model_name not in self.models:
            raise ValueError(f"模型 '{model_name}' 不存在")
            
        self.current_model = self.models[model_name]
        
        # 定义CSS样式
        css = """
        <style>
            .model-container {
                padding: 20px;
                background: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            
            .model-title {
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 16px;
                color: #1a202c;
            }
            
            .info-section {
                margin-bottom: 16px;
            }
            
            .info-label {
                font-weight: 500;
                color: #4a5568;
            }
            
            .info-value {
                color: #2d3748;
            }
            
            .tag {
                display: inline-block;
                padding: 4px 12px;
                margin: 4px;
                background: #f3f4f6;
                color: #4b5563;
                border-radius: 16px;
                font-size: 14px;
            }
            
            .state-section {
                background: #ffffff;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            
            .events-container {
                margin-top: 16px;
            }
            
            .event-card {
                margin-bottom: 16px;
            }
            
            .input-group {
                display: flex;
                align-items: center;
                gap: 8px;
                margin: 8px 0;
            }
            
            .input-field {
                flex: 1;
                padding: 8px 12px;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                background: #f8fafc;
                font-size: 14px;
                color: #4a5568;
            }
            
            .select-button {
                padding: 8px 16px;
                background: #f1f5f9;
                color: #4a5568;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                min-width: 80px;
                text-align: center;
            }
            
            .select-button:hover {
                background: #e2e8f0;
            }
            
            .required {
                background: #ef4444;
                color: white;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 12px;
            }
            
            .optional {
                background: #6b7280;
                color: white;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 12px;
            }
            
            .file-chooser-container {
                margin-top: 8px;
            }
            
            .no-input-message {
                padding: 16px;
                background: #f8fafc;
                border: 1px dashed #e2e8f0;
                border-radius: 6px;
                text-align: center;
                color: #64748b;
                font-style: italic;
                margin: 16px 0;
            }
        </style>
        """
        
        # 创建一个输出控件来容纳所有内容
        output_widget = widgets.VBox()
        widgets_list = []
        
        # 添加模型信息
        model_info_html = f"""
        <div class="model-container">
            <div class="model-title">{self.current_model.name}</div>
            
            <div class="info-section">
                <p><span class="info-label">Description: </span>
                   <span class="info-value">{self.current_model.description or 'No description available'}</span></p>
                <p><span class="info-label">Author: </span>
                   <span class="info-value">{self.current_model.author or 'Unknown'}</span></p>
                <div style="margin-top: 12px">
                    <span class="info-label">Tags: </span>
                    {' '.join(f'<span class="tag">{tag}</span>' for tag in self.current_model.tags)}
                </div>
            </div>
        </div>
        """
        
        model_info = widgets.HTML(value=css + model_info_html)
        widgets_list.append(model_info)
        
        # 遍历所有状态
        for state in self.current_model.states:
            state_name = state.get('name', 'Unnamed State')
            state_desc = state.get('desc', 'No description')
            
            # 创建状态容器
            state_html = f"""
            <div class="state-section">
                <h3>{state_name}</h3>
                <p style="color: #666; font-style: italic;">{state_desc}</p>
                <div class="events-container">
            """
            
            # 检查该状态是否有需要用户输入的事件
            has_input_events = False
            for event in state.get('event', []):
                if event.get('eventType') == 'response':
                    has_input_events = True
                    event_name = event.get('eventName', '')
                    optional_text = "Required" if not event.get('optional', False) else "Optional"
                    event_desc = event.get('eventDesc', '')
                    
                    state_html += f"""
                    <div class="event-card">
                        <div class="event-header">
                            <span class="event-name">{event_name}</span>
                            <span class="event-type {optional_text.lower()}">{optional_text}</span>
                        </div>
                        <div class="event-desc">{event_desc}</div>
                        <div class="input-group">
                            <input type="text" class="input-field" id="file-path-{event_name}" placeholder="No selection" readonly>
                            <button class="select-button" id="select-{event_name}">Select</button>
                        </div>
                        <div class="file-chooser-container" id="chooser-{event_name}"></div>
                    </div>
                    """
            
            # 如果没有需要用户输入的事件，显示提示信息
            if not has_input_events:
                state_html += """
                <div class="no-input-message">
                    <p>此状态不需要用户输入</p>
                </div>
                """
            
            state_html += "</div></div>"
            
            # 创建状态widget并显示
            state_widget = widgets.VBox([
                widgets.HTML(value=state_html)
            ])
            
            # 为每个事件创建文件选择器
            for event in state.get('event', []):
                if event.get('eventType') == 'response':
                    fc = FileChooser(
                        path='/',
                        filename='',
                        title='',
                        show_hidden=False,
                        select_default=True,
                        use_dir_icons=True,
                        show_only_dirs=False,
                        layout=widgets.Layout(display='none')
                    )
                    
                    # 添加文件选择回调
                    def on_select(chooser):
                        selected_file = chooser.selected
                        if selected_file:
                            display(Javascript(f"""
                                document.getElementById('file-path-{event.get("eventName")}').value = '{selected_file}';
                            """))
                    
                    fc.register_callback(on_select)
                    
                    # 添加Select按钮点击事件
                    display(Javascript(f"""
                        document.getElementById('select-{event.get("eventName")}').onclick = function() {{
                            const input = document.createElement('input');
                            input.type = 'file';
                            input.onchange = function(e) {{
                                const file = e.target.files[0];
                                if (file) {{
                                    document.getElementById('file-path-{event.get("eventName")}').value = file.name;
                                }}
                            }};
                            input.click();
                        }};
                    """))
                    
                    state_widget.children += (fc,)
            
            widgets_list.append(state_widget)
        
        # 设置主输出控件的子组件
        output_widget.children = widgets_list
        display(output_widget)