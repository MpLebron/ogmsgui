import json
import os
import ipywidgets as widgets
from ipyfilechooser import FileChooser
from IPython.display import display

# 
class Model:
    """模型基类,用于处理模型的基本属性和操作"""
    def __init__(self, model_data):
        self.id = model_data.get("_id")
        self.name = model_data.get("mdlJson", {}).get("mdl", {}).get("name")
        self.description = model_data.get("description")
        self.author = model_data.get("author")
        self.tags = model_data.get("normalTags", [])
        self.tags_en = model_data.get("normalTagsEn", [])
        
        # 解析模型的输入输出数据项
        self.data_items = self._parse_data_items(
            model_data.get("mdlJson", {}).get("mdl", {}).get("DataItems", [])
        )
        
        # 解析模型状态
        self.states = self._parse_states(
            model_data.get("mdlJson", {}).get("mdl", {}).get("states", [])
        )

    def _parse_data_items(self, data_items):
        """解析数据项配置"""
        items_dict = {}
        for item_group in data_items:
            for item in item_group:
                items_dict[item["text"]] = {
                    "id": item["Id"],
                    "type": item["dataType"],
                    "description": item["desc"]
                }
        return items_dict

    def _parse_states(self, states):
        """解析模型状态配置"""
        states_dict = {}
        for state in states:
            events = {}
            for event in state.get("event", []):
                events[event["eventName"]] = {
                    "id": event["eventId"],
                    "type": event["eventType"],
                    "description": event["eventDesc"],
                    "optional": event["optional"]
                }
            states_dict[state["name"]] = {
                "id": state["Id"],
                "type": state["type"],
                "description": state["desc"],
                "events": events
            }
        return states_dict

class ModelGUI:
    """模型GUI类,负责创建和管理GUI界面"""
    def __init__(self):
        self.models = {}  # 存储所有加载的模型
        self.current_model = None  # 当前选中的模型
        self.widgets = {}  # 存储GUI组件
        
        # 在初始化时直接加载模型配置
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
        """创建参数输入组件"""
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
        """显示指定模型的GUI界面
        
        Args:
            model_name (str): 模型名称
            
        Returns:
            ipywidget: 模型的GUI界面
        """
        if model_name not in self.models:
            raise ValueError(f"模型 '{model_name}' 不存在")
            
        self.current_model = self.models[model_name]
        
        # 创建单个模型的GUI
        tool_widget = widgets.VBox()
        children = []
        
        # 添加模型信息显示
        info_html = f"""
        <h3>{self.current_model.name}</h3>
        <p><b>描述:</b> {self.current_model.description}</p>
        <p><b>作者:</b> {self.current_model.author}</p>
        <p><b>标签:</b> {', '.join(self.current_model.tags)}</p>
        """
        self.widgets['model_info'] = widgets.HTML(value=info_html)
        children.append(self.widgets['model_info'])
        
        # 创建参数输入区
        self.widgets['params_area'] = widgets.VBox()
        param_widgets = []
        for data_name, data_info in self.current_model.data_items.items():
            if data_info['type'] == 'internal':
                widget = FileChooser(
                    title=f"{data_name}: {data_info['description']}"
                )
                self.widgets[f'param_{data_name}'] = widget
                param_widgets.append(widget)
        self.widgets['params_area'].children = param_widgets
        children.append(self.widgets['params_area'])
        
        # 添加运行按钮
        self.widgets['run_button'] = widgets.Button(description='运行模型')
        self.widgets['run_button'].on_click(self._on_run_clicked)
        children.append(self.widgets['run_button'])
        
        # 添加输出区
        self.widgets['output_area'] = widgets.Output()
        children.append(self.widgets['output_area'])
        
        tool_widget.children = children
        return tool_widget