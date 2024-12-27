import json
import os
import ipywidgets as widgets
from ipyfilechooser import FileChooser
from IPython.display import display
import ogmsServer2.openModel as openModel
import time
import requests
from io import StringIO
from IPython import get_ipython
from scripts import AcademicQueryService
import asyncio
from markdown import markdown
import nest_asyncio
from IPython.core.magic import register_line_magic, register_cell_magic
from IPython.display import display, Markdown
from openai import OpenAI
from IPython.display import HTML

# 在文件开头添加这行
nest_asyncio.apply()

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
        self.page_size = 20  # 每页显示的模型数量
        self.current_page = 1  # 当前页码
        self.filtered_models = []  # 存储过滤后的模型列表
        
        # 在初始化时加载模型
        self._load_models()
    
    def _load_models(self):
        """加载模型配置文件"""
        # 获取当前文所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建JSON文件路径
        json_path = os.path.join(current_dir, "data", "computeModel.json")
        
        try:
            with open(json_path, encoding='utf-8') as f:
                models_data = json.load(f)
                for model_name, model_data in models_data.items():
                    self.models[model_name] = Model(model_name, model_data)
        except Exception as e:
            print(f"Failed to load model configuration file: {str(e)}")
            self.models = {}  # Ensure models is an empty dictionary instead of None
    
    def create_gui(self):
        """创建主GUI界面"""
        main_widget = widgets.HBox(layout=widgets.Layout(width='100%'))
        
        # 创建左侧面板
        left_panel = widgets.VBox(layout=widgets.Layout(width='300px', margin='10px'))
        
        # 创建搜索框
        search_box = widgets.Text(
            placeholder='Search...',
            description='Search:',
            layout=widgets.Layout(width='100%', margin='5px 0')
        )
        search_box.observe(self._on_search, 'value')
        
        # 创建分页导航容器
        self.widgets['nav_box'] = widgets.HBox(layout=widgets.Layout(
            width='100%',
            margin='5px 0',
            justify_content='space-between'
        ))
        
        # 创建模型列表容器
        self.widgets['model_list'] = widgets.VBox(layout=widgets.Layout(width='100%'))
        
        # 添加关闭按钮
        close_button = widgets.Button(
            description='Close',
            style=widgets.ButtonStyle(button_color='#ef4444', text_color='white'),
            layout=widgets.Layout(width='100%', margin='10px 0')  # 加宽按钮
        )
        
        def close_gui(b):
            main_widget.close()
        
        close_button.on_click(close_gui)
        
        # 组装左侧面板
        left_panel.children = [
            search_box,
            self.widgets['nav_box'],
            self.widgets['model_list'],
            close_button  # 将关闭按钮放在左侧面板的底部
        ]
        
        # 建右侧模型详情面板
        right_panel = widgets.VBox(layout=widgets.Layout(flex='1', margin='10px'))
        self.widgets['model_detail_area'] = right_panel
        
        main_widget.children = [left_panel, right_panel]
        
        # 初始显示
        self._update_model_list()
        
        return main_widget
    
    def _update_model_list(self, filter_text=''):
        """更新模型列表"""
        # 更新过滤后的模型列表
        self.filtered_models = [
            model_name for model_name in sorted(self.models.keys())
            if filter_text.lower() in model_name.lower() or \
               filter_text.lower() in self.models[model_name].description.lower()
        ]
        
        # 重置页码
        self.current_page = 1
        
        # 更新显示
        self._refresh_display()
    
    def _refresh_display(self):
        """刷新当前页面显示"""
        # 计算页面信息
        total_models = len(self.filtered_models)
        total_pages = max(1, (total_models + self.page_size - 1) // self.page_size)
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total_models)
        
        # 更新导航按钮和页面息
        prev_button = widgets.Button(
            description='Previous',
            disabled=self.current_page == 1,
            layout=widgets.Layout(width='80px'),
            style=widgets.ButtonStyle(button_color='#e2e8f0')  # 添加柔和的背景色
        )
        prev_button.on_click(self._prev_page)
        
        next_button = widgets.Button(
            description='Next',
            disabled=self.current_page == total_pages,
            layout=widgets.Layout(width='80px'),
            style=widgets.ButtonStyle(button_color='#e2e8f0')  # 添加柔和的背景色
        )
        next_button.on_click(self._next_page)
        
        page_info = widgets.HTML(
            value=f'<div style="text-align: center;">Page {self.current_page}/{total_pages}</div>'
        )
        
        self.widgets['nav_box'].children = [prev_button, page_info, next_button]
        
        # 更新模型列表
        model_buttons = []
        for model_name in self.filtered_models[start_idx:end_idx]:
            button = widgets.Button(
                description=model_name,
                layout=widgets.Layout(
                    width='100%',
                    margin='3px 0',  # 增加按钮间距
                    padding='6px 10px'  # 增加按钮内边距
                ),
                style=widgets.ButtonStyle(
                    button_color='white',  # 按钮背景色
                    font_weight='normal'  # 字体粗细
                )
            )
            button.on_click(self._on_model_button_clicked)
            model_buttons.append(button)
        
        self.widgets['model_list'].children = tuple(model_buttons)
    
    def _prev_page(self, b):
        """转到上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self._refresh_display()
    
    def _next_page(self, b):
        """转到下一页"""
        total_pages = (len(self.filtered_models) + self.page_size - 1) // self.page_size
        if self.current_page < total_pages:
            self.current_page += 1
            self._refresh_display()
    
    def _on_search(self, change):
        """处理搜索事件"""
        search_text = change['new']
        self._update_model_list(search_text)
    
    def _on_model_button_clicked(self, button):
        """处理模型按钮点击事件"""
        model_name = button.description
        # print(f"点击了模型: {model_name}")  # 调试信息
        
        # 在右侧面板显示���型界面
        self._show_model_in_panel(model_name)

    def _show_model_in_panel(self, model_name):
        """在侧面板中显示模型界面"""
        if model_name not in self.models:
            print(f"Error: Model '{model_name}' does not exist")
            return
                
        self.current_model = self.models[model_name]
        
        # 创建主容器
        main_container = widgets.VBox()
        widgets_list = []
        
        # 添加模型基本信息
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
                    
                    # 检查是否含nodes数据
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
                        
                        # 个参数创建一行
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
                                    placeholder='Please input value',
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
        widgets_list.append(self.widgets['output_area'])  # 将输出区域添加到widgets_list
        
        # 创建按钮容器（水平布局）
        button_container = widgets.HBox(
            layout=widgets.Layout(
                display='flex',
                justify_content='flex-start',
                gap='10px'
            )
        )

        # 创建Run按钮
        run_button = widgets.Button(
            description='Run',
            style=widgets.ButtonStyle(button_color='#4CAF50', text_color='white')
        )
        run_button.on_click(self._on_run_button_clicked)

        # 创建Close按钮
        close_button = widgets.Button(
            description='Close',
            style=widgets.ButtonStyle(button_color='#ef4444', text_color='white'),
            layout=widgets.Layout(width='80px')
        )
        
        def close_model(b):
            main_container.close()
        
        close_button.on_click(close_model)

        # 将按钮添加到按钮容器
        button_container.children = [run_button, close_button]
        
        # 将按钮容器添加到widgets_list
        widgets_list.append(button_container)
        
        # 设置主容器的子组件
        main_container.children = widgets_list
        
        # 更新右侧面板的内容
        self.widgets['model_detail_area'].children = [main_container]
    
    def show_model(self, model_name):
        """显示指定模型的GUI界面"""
        if model_name not in self.models:
            raise ValueError(f"Model '{model_name}' does not exist")
            
        self.current_model = self.models[model_name]
        
        # 创建主容器
        main_container = widgets.VBox()
        widgets_list = []
        
        # 添加模型基本信息
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
                                    placeholder='Please input value',
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
        widgets_list.append(self.widgets['output_area'])  # 将输出区域添加到widgets_list
        
        # 创建按钮容器（水平布局）
        button_container = widgets.HBox(
            layout=widgets.Layout(
                display='flex',
                justify_content='flex-start',
                gap='10px'
            )
        )

        # 创建Run按钮
        run_button = widgets.Button(
            description='Run',
            style=widgets.ButtonStyle(button_color='#4CAF50', text_color='white')
        )
        run_button.on_click(self._on_run_button_clicked)

        # 创建Close按钮
        close_button = widgets.Button(
            description='Close',
            style=widgets.ButtonStyle(button_color='#ef4444', text_color='white'),
            layout=widgets.Layout(width='80px')
        )
        
        def close_model(b):
            main_container.close()
        
        close_button.on_click(close_model)

        # 将按钮添加到按钮容器
        button_container.children = [run_button, close_button]
        
        # 将按钮容器添加到widgets_list
        widgets_list.append(button_container)
        
        # 设置主容器的子组件
        main_container.children = widgets_list
        
        # 创建水平分栏容器
        split_container = widgets.HBox(
            layout=widgets.Layout(
                width='100%',
                display='flex'
            )
        )
        
        # 创建左侧容器 (65%)
        left_panel = widgets.VBox(
            layout=widgets.Layout(
                width='65%',
                padding='10px'
            )
        )
        
        # 创建右侧容器 (35%)
        right_panel = widgets.VBox(
            layout=widgets.Layout(
                width='35%',
                padding='10px',  # 增加内边距
                border_left='1px solid #ccc'
            )
        )
        
        # 创建搜索框
        search_box = widgets.Text(
            placeholder='Please input your question about this model...',
            description='Search:',
            description_width='50px',
            style={
                'description_width': 'initial',
                'font_family': 'PingFang SC, -apple-system, BlinkMacSystemFont, sans-serif'
            },
            layout=widgets.Layout(
                width='100%',
                margin='8px 0',
                padding='10px 16px',
                border='1px solid #d1d5db',
                border_radius='12px', 
                font_size='15px',
                background_color='white',
                transition='all 0.3s ease',
                box_shadow='0 1px 2px rgba(0, 0, 0, 0.05)'
            )
        )
        # 添加悬停和焦点效果
        search_box._dom_classes = ['hover:border-indigo-500', 'focus:ring-2', 'focus:ring-indigo-500', 'focus:border-indigo-500']
        
        # 创建结果显示区域，添加固定高度和滚动条
        result_area = widgets.Output(
            layout=widgets.Layout(
                width='100%',
                height='500px',  # 固定高度
                # border='1px solid #ddd',
                padding='5px',
                overflow_y='auto'  # 添加垂直滚动条
            )
        )
        
        # 保存到实例变量中
        self.widgets['result_area'] = result_area
        
        # 绑定事件处理函数
        search_box.on_submit(self.on_search_submit)
        
        # 创建标题
        title = widgets.HTML(
            value='<h3 style="margin:0 0 2px 0;">Model QA Assistant</h3>'
        )
        
        # 组装右侧面板 - 修改这部分代码
        right_panel.children = [
            title,
            search_box,
            result_area
        ]
        
        # 将原有的main_container放入左侧面板
        left_panel.children = [main_container]
        
        # 组装分栏容器
        split_container.children = [left_panel, right_panel]
        
        return split_container
    
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
                                    # 传入event_name为参数
                                    download_url = self._upload_to_server(xml_content, event_name)
                                    # 使用下接换XML内容
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
                print(input_files)
                # 继续执行模型
                taskServer = openModel.OGMSAccess(
                    modelName=self.current_model.name,
                    token="6U3O1Sy5696I5ryJFaYCYVjcIV7rhd1MKK0QGX9A7zafogi8xTdvejl6ISUP1lEs"
                )
                print("\nRunning model...")
                result = taskServer.createTask(params=input_files)
                # print(result)
                
                # 添加下载结果文件的代码
                current_dir = os.path.dirname(os.path.abspath(__file__))
                print("\nStart downloading result files...")
                
                for output in result:
                    if output.get('url'):
                        filename = f"{output['tag']}.{output['suffix']}"
                        save_path = os.path.join(current_dir, filename)
                        
                        try:
                            response = requests.get(output['url'])
                            if response.status_code == 200:
                                with open(save_path, 'wb') as f:
                                    f.write(response.content)
                                print(f"✅ File downloaded: {filename}")
                            else:
                                print(f"❌ Download failed {filename}: HTTP {response.status_code}")
                        except Exception as e:
                            print(f"❌ Download failed {filename}: {str(e)}")
                
                print("\nAll files downloaded!")
                
            except Exception as e:
                print(f"❌ Error: Model run failed - {str(e)}")

    def _upload_to_server(self, xml_content, event_name):
        """上传XML据到中转服务器并获取下载链接"""
        try:
            # 务器地址
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
                # 构造下载链接
                download_url = f"{upload_url}/{response_data['data']['id']}"
                return download_url
            else:
                raise Exception(f"Server returned error status code: {response.status_code}")
            
        except Exception as e:
            raise Exception(f"Failed to upload data to server: {str(e)}")

    async def _get_search_result(self, query: str) -> str:
        """
        调用学术查询服务获取结果
        """
        # 获取历史上下文
        ip = get_ipython()
        history_context = ""
        if ip is not None:
            history = []
            for session, line_num, input in ip.history_manager.get_range():
                history.append(input)
            history_context = "\n".join(history)

        # 构建建模上下文
        modeling_context = f"""
                            当前模型: {self.current_model.name}
                            模型描述: {self.current_model.description}
                            历史记录:
                            {history_context}
                            """

        try:
            service = AcademicQueryService()
            full_query = f"Tell me about {self.current_model.name} model's {query}"

            result = await service.get_academic_question_answer(full_query, modeling_context)
            return result
        except Exception:
            return "网络异常请稍后重试"

    def on_search_submit(self, widget):
        """处理搜索提交"""
        query = widget.value.strip()
        with self.widgets['result_area']:
            self.widgets['result_area'].clear_output()
            if query:
                # 获取当前运行的事件循环
                loop = asyncio.get_event_loop()
                try:
                    result = loop.run_until_complete(self._get_search_result(query))
                    if isinstance(result, dict):
                        # 将答案转换为markdown格式
                        answer_html = markdown(result['answer'], extensions=['extra'])
                        # 包装在div中显示
                        answer_wrapper = f"""
                        <div style="margin:4px 0;padding:3px 4px;border:1px solid #e5e7eb;border-radius:12px;word-wrap:break-word;max-width:100%;text-align:justify;background:#ffffff;box-shadow:0 2px 4px rgba(0,0,0,0.05);font-size:14px;line-height:1.3;color:#374151;">
                            {answer_html}
                        </div>
                        """
                        display(HTML(answer_wrapper))
                        
                        print("Related Papers:")
                        # 打印论文列表
                        for paper in result['paperList']:
                            authors = paper.get('authors', [])
                            if len(authors) > 3:
                                author_text = f"{authors[0]} et al."
                            else:
                                author_text = " · ".join(authors)
                            
                            # 论文标题也支持markdown
                            title_html = markdown(paper['title'], extensions=['extra'])
                            display_text_html = markdown(paper['display_text'], extensions=['extra'])
                            
                            paper_html = f"""
    <div style="margin: 4px 0; padding: 8px 12px; background: white; border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: all 0.2s;">
        <h4 style="margin: 0 0 4px 0; padding: 0; font-size: 12px; font-weight: 600; color: #111827; line-height: 1.3; text-align: justify;">{title_html}</h4>
        <p style="margin: 0 0 4px 0; padding: 0; color: #4b5563; font-size: 11px; line-height: 1.4; text-align: justify;">{display_text_html}</p>
        <div style="display: flex; gap: 8px; align-items: center; font-size: 10px; color: #6b7280;">
            <span style="padding: 1px 6px; background: #f3f4f6; border-radius: 9999px;">{paper.get('year', 'N/A')}</span>
            <span>{paper.get('citation_count', 0)} Citations</span>
            <span>{author_text}</span>
            <span style="color: #9ca3af;">{paper.get('journal', 'N/A')}</span>
        </div>
    </div>
    """
                            display(HTML(paper_html))
                    else:
                        print(result)
                except Exception as e:
                    print(f"发生错误: {str(e)}")

class NotebookContext:
    """用于收集和处理Notebook上下文信息"""
    def __init__(self):
        self.data_context = self._get_data_context()
        self.model_context = self._get_model_context()
        self.history_context = self._get_modeling_history_context()

    def to_dict(self):
        """将上下文信息转换为字典格式"""
        return {
            "data_context": self.data_context,
            "model_context": self.model_context,
            "history_context": self.history_context
        }
    
    def _get_data_context(self):
        """获取数据仓库上下文信息"""
        try:
            # 获取IPython shell实例
            ipython = get_ipython()
            if ipython is None:
                raise RuntimeError("This function must be run in an IPython environment")
            
            # 获取当前工作录
            notebook_dir = os.getcwd()
            
            # 定义要排除的目录和文件模式
            exclude_dirs = {
                '.git',
                '__pycache__',
                '.ipynb_checkpoints',
                'node_modules',
                '.idea',
                '.vscode'
            }
            
            # 定义要排除的扩展名
            exclude_extensions = {
                '.pyc',
                '.pyo',
                '.pyd',
                '.so',
                '.git',
                '.DS_Store',
                '.gitignore',
                '.py',
                '.c',
                '.md',
                '.txt'
            }
            
            # 创建数据文件列表
            data_files = []
            
            # 遍历目录树
            for root, dirs, files in os.walk(notebook_dir):
                # 过滤掉不需要的目录
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                # 过滤并处理文件
                for file in files:
                    # 检查文件扩展名
                    _, ext = os.path.splitext(file)
                    if ext not in exclude_extensions and not file.startswith('.'):
                        # 获取相对路径
                        rel_path = os.path.relpath(os.path.join(root, file), notebook_dir)
                        data_files.append(f"- A {ext[1:]} file named '{file}' located at '{rel_path}'")
            
            # 构建自然语描述
            if not data_files:
                context_description = "No relevant data files found in the current directory."
            else:
                context_description = "The following data files are available in the current working directory:\n"
                context_description += "\n".join(data_files)
                context_description += "\n\nThese files might be useful as input data for model operations."
            
            return context_description
        
        except Exception as e:
            print(f"Error getting data context: {str(e)}")
            return "Failed to analyze data context due to an error."

    def _get_model_context(self):
        """获取模型仓库上下文信息"""
        try:
            # 获取当前文件所在目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 构建JSON���件路径
            json_path = os.path.join(current_dir, "data", "computeModel.json")
            
            # 取模型配置文件
            with open(json_path, encoding='utf-8') as f:
                models_data = json.load(f)
            
            # 如果没有模型数据，返回相应描述
            if not models_data:
                return "No models are currently available in the model repository."
            
            # 构建模型描述表
            model_descriptions = ["The following models are available in the model repository:"]
            
            for model_name, model_data in models_data.items():
                # 模型数据中提取信息
                mdl_json = model_data.get("mdlJson", {})
                mdl = mdl_json.get("mdl", {})
                
                description = model_data.get("description", "No description available")
                author = model_data.get("author", "Unknown")
                tags = model_data.get("normalTags", [])
                states = mdl.get("states", [])
                
                # 构建该模型的描述
                model_desc = [f"\n- Model: {model_name}"]
                model_desc.append(f"  Description: {description}")
                model_desc.append(f"  Author: {author}")
                
                if tags:
                    model_desc.append(f"  Tags: {', '.join(tags)}")
                
                # 收集所有输入输出事件
                all_inputs = []
                all_outputs = []
                
                for state in states:
                    state_events = state.get("event", [])
                    all_inputs.extend([e for e in state_events if e.get("eventType") == "response"])
                    all_outputs.extend([e for e in state_events if e.get("eventType") == "noresponse"])
                
                # 描述输入需求
                if all_inputs:
                    model_desc.append("  Input Requirements:")
                    for event in all_inputs:
                        event_name = event.get("eventName", "Unnamed input")
                        event_desc = event.get("eventDesc", "No description")
                        event_optional = "Optional" if event.get("optional", False) else "Required"
                        
                        model_desc.append(f"    - {event_name} ({event_optional})")
                        model_desc.append(f"      Description: {event_desc}")
                
                # 描述输出数据
                if all_outputs:
                    model_desc.append("  Generated Outputs:")
                    for event in all_outputs:
                        event_name = event.get("eventName", "Unnamed output")
                        event_desc = event.get("eventDesc", "No description")
                        
                        model_desc.append(f"    - {event_name}")
                        model_desc.append(f"      Description: {event_desc}")
                
                # 将该模型的描述添加到总描述中
                model_descriptions.extend(model_desc)
            
            # 添加总结性述
            model_descriptions.append("\nThese models can be used for various computational tasks based on their specific purposes and requirements.")
            model_descriptions.append("Each model has specific input requirements and generates corresponding outputs.")
            
            # 将所有描述组合成一个字符串
            return "\n".join(model_descriptions)
        
        except Exception as e:
            print(f"Error getting model context: {str(e)}")
            return "Failed to analyze model repository context due to an error."

    def _get_modeling_history_context(self):
        """获取建模历史上下文信息，包括代码和Markdown内容"""
        try:
            # 获取IPython shell实例
            ipython = get_ipython()
            if ipython is None:
                raise RuntimeError("This function must be run in an IPython environment")
            
            # 获取当前工作目录
            current_dir = os.getcwd()
            
            # 查找最新的ipynb文件
            notebook_path = None
            latest_time = 0
            for root, dirs, files in os.walk(current_dir):
                for file in files:
                    if file.endswith('.ipynb') and not file.endswith('-checkpoint.ipynb'):
                        file_path = os.path.join(root, file)
                        mod_time = os.path.getmtime(file_path)
                        if mod_time > latest_time:
                            latest_time = mod_time
                            notebook_path = file_path
            
            # 记录所有内容
            history_desc = []
            
            # 如果找到notebook文件
            if notebook_path:
                try:
                    import nbformat
                    notebook = nbformat.read(notebook_path, as_version=4)
                    
                    for cell in notebook.cells:
                        if cell.cell_type == 'code':
                            if cell.source.strip():  # 忽略空单元格
                                history_desc.append(f"Code Cell:\n{cell.source}")
                        elif cell.cell_type == 'markdown':
                            if cell.source.strip():  # 忽略空单元格
                                history_desc.append(f"Markdown Cell:\n{cell.source}")
                except Exception as e:
                    print(f"Warning: Could not read notebook content: {str(e)}")
            
            # 获取命令历史
            code_history = list(ipython.history_manager.get_range(output=False))
            for session, line_number, code in code_history:
                if code.strip():  # 忽略空行
                    history_desc.append(f"In [{line_number}]: {code}")
            
            # 将所有描述组合成一个字符串
            return "\n\n".join(history_desc)
        
        except Exception as e:
            print(f"Error getting modeling history: {str(e)}")
            return "Failed to analyze modeling history due to an error."

def Suggest_Model():
    """构建Notebook上下文并调用API服务进行模型推荐"""
    notebookContextInstance = NotebookContext()
    try:
        # 获取上下文信息
        data_context = notebookContextInstance.get_data_context()
        model_context = notebookContextInstance.get_model_context()
        history_context = notebookContextInstance.get_modeling_history_context()  # 注意这里使用了新的函数名

        # 建Notebook上下文对象
        notebook_context = NotebookContext(data_context, model_context, history_context)

        # 发送请求到API服务
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "http://your-api-service-url/recommend",
                    json=notebook_context.to_dict(),
                    timeout=10
                )
                response.raise_for_status()
                
                recommended_models = response.json().get("recommended_models", [])
                print("推荐的模型：")
                for model in recommended_models:
                    print(f"- {model}")
                return recommended_models
                
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                print(f"重试请求 ({attempt + 1}/{max_retries})...")
                time.sleep(1)
                
    except Exception as e:
        print(f"获取模型推荐时发生错误: {str(e)}")
        return []


@register_line_magic
def ogmsChat(line):
    """行魔法函数 - 处理单行查询"""
    return _handle_ogmsChat(line)

@register_cell_magic
def ogmsChat(line, cell):
    """单元格魔法函数 - 处理多行查询"""
    query = cell if cell else line
    return _handle_ogmsChat(query)
    
def _handle_ogmsChat(query):
    # 构建上下文
    # 获取历史上下文
    ip = get_ipython()
    history_context = ""
    if ip is not None:
        history = []
        for session, line_num, input in ip.history_manager.get_range():
            history.append(input)
        history_context = "\n".join(history)
    notebookContextInstance = NotebookContext()
    data_context = notebookContextInstance.data_context
    # model_context = notebookContextInstance.model_context
    # history_context = notebookContextInstance.history_context
    # 调用%history来获取历史上下文

    # 将当前建模环境中的数据、模型、历史上下文信息添加到发送给OpenAI的指令的上下文中，描述要足够清晰，要交代好，现在是在Jupyter环境下地理建模与模拟，用户当前的环境里的数据条目及其数据目录里在data_context中，用户可以通过GUI页面调用的模型列表在model_context中，用户当前环境下和jupyter notebook里的建模历史在history_context中

    # 这里是因为数据目录的字符太长了，所以只取前2000个字符，但是后面记得把这个数据目录的完整内容加到openAI_query中
    openAI_query = f"现在是在Jupyter环境下地理建模与模拟，用户当前的环境里的数据条目及其数据目录里在" + data_context[:2000] + "中，用户可以通过GUI页面调用的模型列表在" + "Nomodel" + "中，用户当前环境下和jupyter notebook里的建模历史在" + history_context + "中。如果用户问你的是关于学术性质的知识问答的话，请你在回答完用户的问题后，加入3-5篇参考文献。如果用户是让你帮他写代码的话，请你一定要回顾用户当前的建模历史，并且记住，你要给他能基于当前历史的代码建议，而不是让他从头开始写代码。用户当前的查询是：" + query

    """处理查询的核心逻辑"""
    client = OpenAI(api_key="sk-rb7CtWXJ6AXWCiavF80eA074B3704438B7C855C3D623Bb25", base_url="https://aihubmix.com/v1")
    try:
        # 调用 ChatGPT API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": openAI_query}
            ],
            temperature=0.7,
            stream=True
        )
        
        # 创建输出区域
        from IPython.display import display, clear_output
        output = display('', display_id=True)
        
        # 用于累积完整响应
        full_response = ""
        
        # 逐块处理流式响应
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content
                # 更新显示的内容
                output.update(Markdown(f"### ChatGPT Response\n{full_response}"))
                    
    except Exception as e:
        display(Markdown(f"❌ Error: {str(e)}"))

# 防止魔法函数名称保留在命名空间中
del ogmsChat

# 我想要再写一个叫ogms_taskPlan的魔法函数，这个函数的作用是���据用户输入的查询，生成针对于当前建模上下文和用户建模目的的建模任务计划，这个魔法函数对应的脚本会先根据用户的提问进行论文爬取，找到相关的论文，然后总结这些论文，从而进行任务规划

@register_line_magic
def ogms_taskPlan(line):
    """行魔法函数 - 处理单行查询"""
    # 获取事件循环
    loop = asyncio.get_event_loop()
    # 运行异步函数
    return loop.run_until_complete(_handle_ogms_taskPlan(line))

@register_cell_magic
def ogms_taskPlan(line, cell):
    """单元格魔法函数 - 处理多行查询"""
    query = cell if cell else line
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_handle_ogms_taskPlan(query))

async def _handle_ogms_taskPlan(query):
    # 构建上下文
    # 获取历史上下文
    ip = get_ipython()
    history_context = ""
    if ip is not None:
        history = []
        for session, line_num, input in ip.history_manager.get_range():
            history.append(input)
        history_context = "\n".join(history)

    # 调用scripts里的_get_academic_question_answer_list函数获取论文列表
    service = AcademicQueryService()
    paper_list = await service._get_academic_question_answer_list(query)

    openAI_query = f"现在是在Jupyter环境下的地理建模与模拟过程，你的主要任务是为用户的建模需求提供详细的任务规划，用户当前环境下和jupyter notebook里的建模历史在" + history_context + " 用户当前的查询是：" + query + " 检索出来的与用户查询相关的论文列表是：" + str(paper_list) + " 请根据这些信息，为用户的建模需求提供详细的任务规划，并给出每个任务的详细步骤"

    client = OpenAI(api_key="sk-rb7CtWXJ6AXWCiavF80eA074B3704438B7C855C3D623Bb25", base_url="https://aihubmix.com/v1")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": openAI_query}
        ],
        temperature=0.7,
        stream=True
    )

        # 先创建两个输出区域
    task_output = display('', display_id='task')
    papers_output = display('', display_id='papers')
    
    # 用于累积完整响应
    full_response = ""
    
    # 先处理论文列表
    papers_html = ""
    for paper in paper_list:
        authors = paper.get('authors', [])
        if len(authors) > 3:
            author_text = f"{authors[0]} et al."
        else:
            author_text = " · ".join(authors)
        
        papers_html += f"""
    <div style="margin: 4px 0; padding: 8px 12px; background: white; border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h4 style="margin: 0 0 4px 0; padding: 0; font-size: 12px; font-weight: 600; color: #111827;">{paper['title']}</h4>
        <p style="margin: 0 0 4px 0; padding: 0; color: #4b5563; font-size: 11px;">{paper.get('display_text', '')}</p>
        <div style="display: flex; gap: 8px; align-items: center; font-size: 10px; color: #6b7280;">
            <span style="padding: 1px 6px; background: #f3f4f6; border-radius: 9999px;">{paper.get('year', 'N/A')}</span>
            <span>{paper.get('citation_count', 0)} Citations</span>
            <span>{author_text}</span>
            <span style="color: #9ca3af;">{paper.get('journal', 'N/A')}</span>
        </div>
    </div>
    """
    
    # 更新论文列表显示
    papers_output.update(HTML(f"<h3>Related Papers:</h3>{papers_html}"))
    
    # 处理流式响应
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response += content
            # 更新任务规划显示
            task_output.update(Markdown(f"### Task Planning\n{full_response}"))