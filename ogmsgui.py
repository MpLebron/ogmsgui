import json
import os
import ipywidgets as widgets
from ipyfilechooser import FileChooser
from IPython.display import display
import ogmsServer2.openModel as openModel
import time
import requests
from io import StringIO
# 
class Model:
    """模型基类,用于处理模型的基本属性和操作"""
    def __init__(self, model_name, model_data):
        mdl_json = model_data.get("mdlJson", {})
        mdl = mdl_json.get("mdl", {})
        
        self.id = model_data.get("_id", "")
        self.name = model_name  # 使用键名作为型名称
        self.description = model_data.get("description", "")
        self.author = model_data.get("author", "")
        self.tags = model_data.get("normalTags", [])
        self.tags_en = model_data.get("normalTagsEn", [])
        
        self.states = mdl.get("states", [])

class ModelGUI:
    """模型GUI类,负责创建和管理GUI界面"""
    def __init__(self):
        self.models = {}  # 存储所有加载的模型
        self.current_model = None  # 当前选中的模型
        self.widgets = {}  # 存储GUI组件
        
        # 在初��化时直接加载模型
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
                    self.models[model_name] = Model(model_name, model_data)
        except Exception as e:
            print(f"加载模型配置文件失败: {str(e)}")
            self.models = {}  # 确保models空字典而不是None
    
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
        
        # 创建参数入区
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
                    layout=widgets.Layout(
                        width='100%',  # 设置宽度为100%
                        margin='4px 0',
                    )
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
        
        # 创建主容器
        main_container = widgets.VBox()
        widgets_list = []
        
        # 添加模型基本信息 - 使用卡片样式
        model_info = widgets.HTML(value=f"""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; margin-bottom: 10px;">
                <h3 style="margin-top: 0;">{self.current_model.name}</h3>
                <p style="color: #666; margin-bottom: 8px;">{self.current_model.description}</p>
                <div style="display: flex; gap: 10px;">
                    <div>
                        <span style="color: #666;">Authors' Emails: </span>
                        <span>{self.current_model.author}</span>
                    </div>
                    <div>
                        <span style="color: #666;">Tags: </span>
                        <span>{', '.join(self.current_model.tags)}</span>
                    </div>
                </div>
            </div>
        """)
        widgets_list.append(model_info)
        
        # 遍历状态
        for i, state in enumerate(self.current_model.states):
            state_container = widgets.VBox(
                layout=widgets.Layout(margin='0 0 8px 0')
            )
            state_widgets = []
            
            # 添加状态信息
            state_info = widgets.HTML(value=f"""
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; margin-bottom: 8px;">
                    <h3 style="color: #1e293b; margin: 0 0 4px 0; font-size: 16px; font-weight: 600;">{state.get('name', '')}</h3>
                    <p style="color: #64748b; margin: 0; font-size: 14px;">{state.get('desc', '')}</p>
                </div>
            """)
            state_widgets.append(state_info)
            
            # 检查该状态是否有需要用户输入的事件
            has_input_events = False
            for event in state.get('event', []):
                if event.get('eventType') == 'response':
                    has_input_events = True
                    event_container = widgets.VBox(layout=widgets.Layout(margin='3px 0'))
                    event_widgets = []
                    
                    event_name = event.get('eventName', '')
                    optional_text = "Required" if not event.get('optional', False) else "Optional"
                    event_desc = event.get('eventDesc', '')
                    
                    # 添加事件标题和描述
                    event_header = widgets.HTML(value=f"""
                        <div style="margin: 2px 0;">
                            <span style="font-weight: 500;">{event_name}</span>
                            <span style="background: {('#ef4444' if optional_text == 'Required' else '#94a3b8')}; 
                                     color: white; 
                                     padding: 1px 8px; 
                                     border-radius: 12px; 
                                     font-size: 12px; 
                                     margin-left: 8px;">
                                {optional_text}
                            </span>
                            <div style="color: #666; margin: 1px 0 2px 0;">{event_desc}</div>
                        </div>
                    """)
                    event_widgets.append(event_header)
                    
                    # 检查是否包含nodes类数据
                    has_nodes = False
                    nodes_data = []
                    for data_item in event.get('data', []):
                        if 'nodes' in data_item:
                            has_nodes = True
                            nodes_data = data_item['nodes']
                    
                    if has_nodes:
                        # 创建表格容器
                        table_container = widgets.VBox()
                        table_widgets = []
                        
                        # 添加表头
                        header = widgets.HTML(value="""
                            <div style="display: grid; grid-template-columns: 1fr 2fr 1fr; gap: 8px; padding: 8px; background: #f8fafc; border: 1px solid #e2e8f0;">
                                <div style="font-weight: 500;">Parameter Name</div>
                                <div style="font-weight: 500;">Description</div>
                                <div style="font-weight: 500;">Value</div>
                            </div>
                        """)
                        table_widgets.append(header)
                        
                        # 为每个参数创建一行
                        for node in nodes_data:
                            # 创建行容器
                            row = widgets.HBox([
                                widgets.HTML(value=f"""
                                    <div style="padding: 8px; min-width: 150px;">{node.get('text', '')}</div>
                                """),
                                widgets.HTML(value=f"""
                                    <div style="padding: 8px; min-width: 200px;">{node.get('desc', '')}</div>
                                """),
                                widgets.Text(
                                    placeholder='请输入值',
                                    layout=widgets.Layout(width='150px')
                                )
                            ])
                            # 存储Text widget的引用
                            self.widgets[f'node-{event_name}-{node.get("text")}'] = row.children[-1]
                            table_widgets.append(row)
                        
                        table_container.children = table_widgets
                        event_widgets.append(table_container)
                    else:
                        # 创建文件选择器
                        fc = FileChooser(
                            path='./',
                            layout=widgets.Layout(width='100%')
                        )
                        self.widgets[f'file_chooser_{event_name}'] = fc
                        event_widgets.append(fc)
                    
                    event_container.children = event_widgets
                    state_widgets.append(event_container)
            
            # 如果没有输入事件，添加提示信息
            if not has_input_events:
                no_input_msg = widgets.HTML(value="""
                    <div style="padding: 8px 12px; 
                                background: #f8fafc; 
                                border: 1px dashed #e2e8f0; 
                                border-radius: 4px; 
                                color: #64748b; 
                                font-size: 14px; 
                                margin: 4px 0;">
                        This state does not require user input
                    </div>
                """)
                state_widgets.append(no_input_msg)
            
            state_container.children = state_widgets
            widgets_list.append(state_container)
            
            if i < len(self.current_model.states) - 1:
                divider = widgets.HTML(value="""
                    <div style="padding: 0 16px;">
                        <hr style="border: none; border-top: 2px solid #1e293b; margin: 12px 0;">
                    </div>
                """)
                widgets_list.append(divider)
        
        # 创建输出区域
        self.widgets['output_area'] = widgets.Output()
        
        # 添加运行按钮和输出区域
        run_button = widgets.Button(
            description='Run',
            style=widgets.ButtonStyle(button_color='#4CAF50', text_color='white')
        )
        run_button.on_click(self._on_run_button_clicked)
        
        # 将按钮和输出区域添加到widgets_list
        widgets_list.extend([
            run_button,
            self.widgets['output_area']
        ])
        
        # 设置主容器的子组件
        main_container.children = widgets_list
        display(main_container)

    def _on_run_button_clicked(self, b):
        """处理运行按钮点击事件"""
        with self.widgets['output_area']:
            self.widgets['output_area'].clear_output()
            
            missing_required_fields = []
            input_files = {}
            
            for state in self.current_model.states:
                state_name = state.get('name')
                input_files[state_name] = {}
                
                for event in state.get('event', []):
                    if event.get('eventType') == 'response':
                        event_name = event.get('eventName', '')
                        is_required = not event.get('optional', False)
                        
                        # 检查是否有nodes数据
                        has_nodes = False
                        nodes_data = []
                        for data_item in event.get('data', []):
                            if 'nodes' in data_item:
                                has_nodes = True
                                nodes_data = data_item['nodes']
                    
                        if has_nodes:
                            # 创建XML格式的数据
                            xml_lines = ['<Dataset>']
                            for node in nodes_data:
                                widget = self.widgets.get(f'node-{event_name}-{node.get("text")}')
                                if widget:
                                    value = widget.value
                                    if value:
                                        kernel_type = node.get('kernelType', 'string')
                                        xml_lines.append(
                                            f'  <XDO name="{node.get("text")}" '
                                            f'kernelType="{kernel_type}" '
                                            f'value="{value}" />'
                                        )
                                    elif is_required:
                                        missing_required_fields.append(f"'{node.get('text')}'")
                            xml_lines.append('</Dataset>')
                            
                            if len(xml_lines) > 2:  # 如果有数据
                                xml_content = '\n'.join(xml_lines)
                                try:
                                    # 传入event_name作为参数
                                    download_url = self._upload_to_server(xml_content, event_name)
                                    # 使用下载链接替换XML内容
                                    input_files[state_name][event_name] = download_url
                                except Exception as e:
                                    print(f"❌ Error: Failed to upload data - {str(e)}")
                                    return
                        else:
                            # 处理文件输入
                            file_chooser = self.widgets.get(f'file_chooser_{event_name}')
                            if file_chooser:
                                if file_chooser.selected:
                                    input_files[state_name][event_name] = file_chooser.selected
                                elif is_required:
                                    missing_required_fields.append(f"'{event_name}'")
            
            if missing_required_fields:
                print(f"❌ Error: The following required fields are missing: {', '.join(missing_required_fields)}")
                return

            try:
                # print(input_files)
                # 继续执行模型
                taskServer = openModel.OGMSAccess(
                    modelName=self.current_model.name,
                    token="6U3O1Sy5696I5ryJFaYCYVjcIV7rhd1MKK0QGX9A7zafogi8xTdvejl6ISUP1lEs"
                )
                print("\nRunning model...")
                result = taskServer.createTask(params=input_files)
                # print(result)
                
            except Exception as e:
                print(f"❌ Error: Model run failed - {str(e)}")

    def _upload_to_server(self, xml_content, event_name):
        """上传XML数据到中转服务器并获取下载链接"""
        try:
            # 服务器地址
            upload_url = 'http://112.4.132.6:8083/data'
            
            # 使用event_name作为文件名
            filename = f"{event_name}"
            
            # 创建表单数据
            files = {
                'datafile': (filename, StringIO(xml_content), 'application/xml')
            }
            data = {
                'name': filename  # 使用相同的文件名
            }
            
            # 发送POST请求
            response = requests.post(upload_url, files=files, data=data)
            
            # 检查响应状态
            if response.status_code == 200:
                response_data = response.json()
                # 构建下载链接
                download_url = f"{upload_url}/{response_data['data']['id']}"
                return download_url
            else:
                raise Exception(f"Server returned error status code: {response.status_code}")
            
        except Exception as e:
            raise Exception(f"Failed to upload data to server: {str(e)}")