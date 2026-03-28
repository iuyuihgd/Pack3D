from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList, OneLineAvatarIconListItem, IconLeftWidget
from kivymd.uix.tab import MDTabs, MDTab
from kivymd.uix.floatlayout import MDFloatLayout
from kivy.clock import Clock
from kivy.graphics import Color, Line, Mesh, PushMatrix, PopMatrix, Rotate, Translate, Scale
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivymd.utils import dp
from py3dbp import Packer, Bin, Item
import threading
import numpy as np

# ========== 3D 可视化部件 (已针对安卓触控优化+修复核心bug) ==========
class PackingView3D(Widget):
    """用于显示3D装箱结果的交互式画布"""
    def __init__(self, packing_result=None, **kwargs):
        super().__init__(**kwargs)
        self.packing_result = packing_result
        # 视图初始参数
        self.rot_x = 30
        self.rot_y = -45
        self.rot_z = 0
        self.translate = [0, 0, -500]  # 初始镜头距离
        self.scale = 1.0
        
        # 触控交互状态变量
        self._touch_start_pos = None
        self._touch_start_rot = None
        self._two_finger_start = None
        self._scale_start = 1.0
        self._touch_events = []
        
        # 修复2：重构画布层级，让变换矩阵和绘图内容绑定（解决重绘失效）
        self._init_canvas_transforms()
        self.redraw()

    def _init_canvas_transforms(self):
        """初始化画布变换矩阵，单独抽离避免重绘错乱"""
        self.canvas.clear()
        with self.canvas:
            PushMatrix()
            self.rot_x_obj = Rotate(angle=self.rot_x, axis=(1, 0, 0), origin=(0, 0, 0))
            self.rot_y_obj = Rotate(angle=self.rot_y, axis=(0, 1, 0), origin=(0, 0, 0))
            self.rot_z_obj = Rotate(angle=self.rot_z, axis=(0, 0, 1), origin=(0, 0, 0))
            self.translate_obj = Translate(*self.translate)
            self.scale_obj = Scale(self.scale, self.scale, self.scale)
        with self.canvas.after:
            PopMatrix()

    def redraw(self, *args):
        """根据 packing_result 重绘3D场景"""
        # 先清空绘图内容，保留变换矩阵
        self.canvas.children = [self.canvas.children[-1]] if self.canvas.children else []
        # 更新变换矩阵属性
        self.rot_x_obj.angle = self.rot_x
        self.rot_y_obj.angle = self.rot_y
        self.rot_z_obj.angle = self.rot_z
        self.translate_obj.xyz = self.translate
        self.scale_obj.xyz = (self.scale, self.scale, self.scale)

        if not self.packing_result:
            self._draw_axes()
            return
        # 绘制每一个箱子及其中的物品
        for bin_data in self.packing_result:
            self._draw_bin_wireframe(bin_data)
            for item in bin_data['items']:
                self._draw_item_cube(item, bin_data['color_idx'])

    def _draw_axes(self, length=50):
        """绘制XYZ坐标轴（红色:X, 绿色:Y, 蓝色:Z）"""
        with self.canvas:
            Color(1, 0, 0, 1)  # 红 X
            Line(points=[0, 0, 0, length, 0, 0], width=2)
            Color(0, 1, 0, 1)  # 绿 Y
            Line(points=[0, 0, 0, 0, length, 0], width=2)
            Color(0, 0, 1, 1)  # 蓝 Z
            Line(points=[0, 0, 0, 0, 0, length], width=2)

    def _draw_bin_wireframe(self, bin_data):
        """绘制一个箱子的线框"""
        w, d, h = bin_data['dims']
        vertices = [
            (0, 0, 0), (w, 0, 0), (w, d, 0), (0, d, 0),  # 底面
            (0, 0, h), (w, 0, h), (w, d, h), (0, d, h)   # 顶面
        ]
        edges = [
            (0,1), (1,2), (2,3), (3,0),  # 底面边
            (4,5), (5,6), (6,7), (7,4),  # 顶面边
            (0,4), (1,5), (2,6), (3,7)   # 侧面边
        ]
        with self.canvas:
            Color(0.5, 0.5, 0.5, 0.7)  # 半透明白色
            for start, end in edges:
                Line(points=[vertices[start][0], vertices[start][1], vertices[start][2],
                             vertices[end][0], vertices[end][1], vertices[end][2]], width=1.5)

    def _draw_item_cube(self, item, color_idx):
        """绘制一个物品的实心立方体"""
        x, y, z = item['position']
        w, d, h = item['dims']
        # 颜色循环
        colors = [
            (1, 0, 0, 0.7), (0, 1, 0, 0.7), (0, 0, 1, 0.7),
            (1, 1, 0, 0.7), (1, 0, 1, 0.7), (0, 1, 1, 0.7)
        ]
        color = colors[color_idx % len(colors)]
        # 立方体8个顶点
        vertices = np.array([
            [x, y, z], [x+w, y, z], [x+w, y+d, z], [x, y+d, z],
            [x, y, z+h], [x+w, y, z+h], [x+w, y+d, z+h], [x, y+d, z+h]
        ], dtype=np.float32)
        # 6个面的12个三角形
        indices = [
            0,1,2, 0,2,3, 4,5,6, 4,6,7,
            0,1,5, 0,5,4, 1,2,6, 1,6,5,
            2,3,7, 2,7,6, 3,0,4, 3,4,7
        ]
        vertices_flat = vertices.flatten()
        with self.canvas:
            Color(*color)
            Mesh(vertices=vertices_flat, indices=indices, mode='triangles')

    # ========== 安卓触控交互逻辑 (修复触控bug+适配手机) ==========
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._touch_events.append(touch)
            
            if touch.is_double_tap:
                # 双击：重置视图
                self.rot_x = 30
                self.rot_y = -45
                self.rot_z = 0  # 优化：重置Z轴旋转
                self.translate = [0, 0, -500]
                self.scale = 1.0
                self.redraw()
                return True
                
            if len(self._touches) == 1:
                # 单指按下：准备旋转
                self._touch_start_pos = touch.pos
                self._touch_start_rot = (self.rot_x, self.rot_y)
            elif len(self._touches) == 2:
                # 双指按下：准备缩放/平移
                self._two_finger_start = {
                    'center': self._get_center(self._touches),
                    'distance': self._get_distance(self._touches),
                    'translate': self.translate.copy()
                }
                self._scale_start = self.scale
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if len(self._touches) == 1 and self._touch_start_pos:
                # 单指移动：旋转 + 修复3：增加角度范围限制（适配安卓）
                dx = touch.x - self._touch_start_pos[0]
                dy = touch.y - self._touch_start_pos[1]
                self.rot_y = self._touch_start_rot[1] + dx * 0.5
                self.rot_x = self._touch_start_rot[0] - dy * 0.5
                # 角度边界限制，避免视角混乱
                self.rot_x = max(-90, min(self.rot_x, 90))
                self.rot_y = max(-180, min(self.rot_y, 180))
                self.rot_z = max(-90, min(self.rot_z, 90))
                self.redraw()
            elif len(self._touches) == 2 and self._two_finger_start:
                # 双指移动
                current_distance = self._get_distance(self._touches)
                start_distance = self._two_finger_start['distance']
                
                if start_distance != 0:
                    # 双指张合：缩放
                    scale_factor = current_distance / start_distance
                    self.scale = self._scale_start * scale_factor
                    self.scale = max(0.1, min(self.scale, 10.0))
                    
                    # 双指平移 + 修复4：调整阻尼系数为0.3（适配手机触控，避免滑动过快）
                    current_center = self._get_center(self._touches)
                    start_center = self._two_finger_start['center']
                    dx = (current_center[0] - start_center[0]) * 0.3
                    dy = (current_center[1] - start_center[1]) * 0.3
                    self.translate[0] = self._two_finger_start['translate'][0] + dx
                    self.translate[1] = self._two_finger_start['translate'][1] - dy
                    
                    self.redraw()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if touch in self._touch_events:
                self._touch_events.remove(touch)
            if len(self._touches) == 0:
                # 所有手指抬起
                self._touch_start_pos = None
                self._two_finger_start = None
            return True
        return super().on_touch_up(touch)

    def _get_distance(self, touches):
        """计算两个触摸点距离 + 修复5：修正字典取值逻辑，避免安卓识别错乱"""
        if len(touches) < 2:
            return 0
        points = list(touches.values())  # 直接取values列表
        if len(points) < 2:
            return 0
        t1, t2 = points[0], points[1]
        return ((t1.x - t2.x) ** 2 + (t1.y - t2.y) ** 2) ** 0.5

    def _get_center(self, touches):
        """计算两个触摸点中心 + 修复6：和_get_distance保持一致的取值逻辑"""
        if len(touches) < 2:
            return (0, 0)
        points = list(touches.values())
        if len(points) < 2:
            return (0, 0)
        t1, t2 = points[0], points[1]
        return ((t1.x + t2.x) * 0.5, (t1.y + t2.y) * 0.5)

    @property
    def _touches(self):
        """获取当前在自身范围内的所有触摸点"""
        return {t.id: t for t in self._touch_events if self.collide_point(t.x, t.y)}

# ========== 主界面类 (修复UI兼容+安卓适配) ==========
class Pack3DUI(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(12)
        self.spacing = dp(10)
        self.bins = []
        self.items = []
        self.packing_result_for_3d = []  # 存储3D视图数据
        
        # 标题
        self.add_widget(MDLabel(
            text="锂电池PACK装箱3D (专业版)", 
            font_style="H5", 
            halign="center", 
            size_hint_y=None, 
            height=dp(40)
        ))
        
        # === 输入区域 ===
        input_box = MDBoxLayout(orientation='vertical', spacing=dp(8), 
                               size_hint_y=None, height=dp(280))
        
        # 箱子输入
        input_box.add_widget(MDLabel(
            text="1. 定义容器（箱子）", 
            font_style="Subtitle2", 
            theme_text_color="Primary"
        ))
        bin_box = MDBoxLayout(adaptive_height=True, spacing=dp(8))  # 优化：自适应高度
        self.bin_w = MDTextField(hint_text="宽(mm)", input_filter='float', size_hint_x=0.22)
        self.bin_d = MDTextField(hint_text="深(mm)", input_filter='float', size_hint_x=0.22)
        self.bin_h = MDTextField(hint_text="高(mm)", input_filter='float', size_hint_x=0.22)
        self.bin_cnt = MDTextField(hint_text="数量", input_filter='int', size_hint_x=0.22, text="1")
        for field in [self.bin_w, self.bin_d, self.bin_h, self.bin_cnt]:
            bin_box.add_widget(field)
        input_box.add_widget(bin_box)
        
        btn_bin = MDRaisedButton(text="添加此规格箱子", size_hint_y=None, height=dp(40))
        btn_bin.bind(on_press=self.add_bin)
        input_box.add_widget(btn_bin)
        
        # 物品输入
        input_box.add_widget(MDLabel(
            text="2. 定义物品（电芯/模组）", 
            font_style="Subtitle2", 
            theme_text_color="Primary", 
            size_hint_y=None, 
            height=dp(30)
        ))
        item_box = MDBoxLayout(adaptive_height=True, spacing=dp(8))  # 优化：自适应高度
        self.item_w = MDTextField(hint_text="宽(mm)", input_filter='float', size_hint_x=0.22)
        self.item_d = MDTextField(hint_text="深(mm)", input_filter='float', size_hint_x=0.22)
        self.item_h = MDTextField(hint_text="高(mm)", input_filter='float', size_hint_x=0.22)
        self.item_cnt = MDTextField(hint_text="数量", input_filter='int', size_hint_x=0.22, text="1")
        for field in [self.item_w, self.item_d, self.item_h, self.item_cnt]:
            item_box.add_widget(field)
        input_box.add_widget(item_box)
        
        btn_item = MDRaisedButton(text="添加此规格物品", size_hint_y=None, height=dp(40))
        btn_item.bind(on_press=self.add_item)
        input_box.add_widget(btn_item)
        
        self.add_widget(input_box)
        
        # === 数据列表区域 ===
        list_box = MDBoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=1.5)
        
        # 箱子列表
        bin_list_box = MDBoxLayout(orientation='vertical', size_hint_x=0.5)
        bin_list_box.add_widget(MDLabel(
            text="已添加的箱子", 
            font_style="Subtitle2", 
            halign="center", 
            size_hint_y=None, 
            height=dp(30)
        ))
        self.bin_scroll = MDScrollView()
        self.bin_list = MDList()
        self.bin_scroll.add_widget(self.bin_list)
        bin_list_box.add_widget(self.bin_scroll)
        list_box.add_widget(bin_list_box)
        
        # 物品列表
        item_list_box = MDBoxLayout(orientation='vertical', size_hint_x=0.5)
        item_list_box.add_widget(MDLabel(
            text="已添加的物品", 
            font_style="Subtitle2", 
            halign="center", 
            size_hint_y=None, 
            height=dp(30)
        ))
        self.item_scroll = MDScrollView()
        self.item_list = MDList()
        self.item_scroll.add_widget(self.item_list)
        item_list_box.add_widget(self.item_scroll)
        list_box.add_widget(item_list_box)
        
        self.add_widget(list_box)
        
        # === 操作按钮 ===
        action_box = MDBoxLayout(adaptive_height=True, spacing=dp(15), 
                                size_hint_y=None, height=dp(50))
        btn_pack = MDRaisedButton(text="开始智能装箱", size_hint_x=0.5)
        btn_pack.bind(on_press=self.do_pack)
        btn_clear = MDRaisedButton(text="清空所有数据", size_hint_x=0.5)
        btn_clear.bind(on_press=self.do_clear)
        action_box.add_widget(btn_pack)
        action_box.add_widget(btn_clear)
        self.add_widget(action_box)
        
        # === 结果展示区域 (选项卡) + 修复7：替换为KivyMD原生MDTab，解决UI崩溃 ===
        self.tabs = MDTabs(size_hint_y=4)
        
        # 文本报告标签页
        self.text_tab = MDTab(text='文本报告')  # 替换：MDTab替代TabbedPanelItem
        self.result_label = MDLabel(
            text="[b]就绪[/b]\n添加箱子和物品后，点击“开始智能装箱”。", 
            markup=True, 
            valign='top',
            padding=[dp(10), dp(10)]
        )
        text_scroll = MDScrollView()
        text_scroll.add_widget(self.result_label)
        self.text_tab.add_widget(text_scroll)
        self.tabs.add_widget(self.text_tab)
        
        # 3D视图标签页
        self.view_3d_tab = MDTab(text='3D视图')  # 替换：MDTab替代TabbedPanelItem
        self.view_3d_container = MDFloatLayout()
        self.packing_3d_view = PackingView3D(size_hint=(1, 1))
        self.view_3d_container.add_widget(self.packing_3d_view)
        self.view_3d_tab.add_widget(self.view_3d_container)
        self.tabs.add_widget(self.view_3d_tab)
        
        self.add_widget(self.tabs)

    def _add_to_list_view(self, data_list, ui_list, name_prefix, dimensions):
        """向数据列表和UI列表中添加条目"""
        item_text = f"{name_prefix}{len(data_list)+1}: {dimensions}"
        list_item = OneLineAvatarIconListItem(text=item_text)
        icon = IconLeftWidget(icon="delete")
        idx = len(data_list)
        icon.bind(on_press=lambda x, list_idx=idx, list_obj=data_list, 
                  ui_obj=ui_list: self._delete_item(list_idx, list_obj, ui_obj))
        list_item.add_widget(icon)
        ui_list.add_widget(list_item)
        return list_item

    def _delete_item(self, index, data_list, ui_list):
        """删除指定列表中的条目"""
        if 0 <= index < len(data_list):
            data_list.pop(index)
            ui_list.remove_widget(ui_list.children[len(ui_list.children)-1-index])
            # 更新显示文本
            for i, child in enumerate(reversed(ui_list.children)):
                orig_text = child.text
                prefix = orig_text.split(':')[0].rstrip('0123456789')
                child.text = f"{prefix}{i+1}:{orig_text.split(':', 1)[1]}"
            self.result_label.text = f"已删除条目，剩余 {len(data_list)} 个。"

    def add_bin(self, instance):
        try:
            w = float(self.bin_w.text.strip()) if self.bin_w.text.strip() else 0.0
            d = float(self.bin_d.text.strip()) if self.bin_d.text.strip() else 0.0
            h = float(self.bin_h.text.strip()) if self.bin_h.text.strip() else 0.0
            c = int(self.bin_cnt.text.strip()) if self.bin_cnt.text.strip() else 1
            
            if w <= 0 or d <= 0 or h <= 0 or c <= 0:
                self.result_label.text = "[color=ff0000]错误：尺寸和数量必须大于0[/color]"
                return
                
            for _ in range(c):
                self.bins.append(Bin(f"箱{len(self.bins)+1}", w, d, h, 10000))
                dim_str = f"{int(w)}x{int(d)}x{int(h)}mm"
                self._add_to_list_view(self.bins, self.bin_list, "箱", dim_str)
                
            self.result_label.text = f"已添加 {c} 个箱子（{int(w)}x{int(d)}x{int(h)}mm）"
            
        except ValueError:
            self.result_label.text = "[color=ff0000]错误：请输入有效的数字[/color]"

    def add_item(self, instance):
        try:
            w = float(self.item_w.text.strip()) if self.item_w.text.strip() else 0.0
            d = float(self.item_d.text.strip()) if self.item_d.text.strip() else 0.0
            h = float(self.item_h.text.strip()) if self.item_h.text.strip() else 0.0
            c = int(self.item_cnt.text.strip()) if self.item_cnt.text.strip() else 1
            
            if w <= 0 or d <= 0 or h <= 0 or c <= 0:
                self.result_label.text = "[color=ff0000]错误：尺寸和数量必须大于0[/color]"
                return
                
            for _ in range(c):
                self.items.append(Item(f"物品{len(self.items)+1}", w, d, h, 500))
                dim_str = f"{int(w)}x{int(d)}x{int(h)}mm"
                self._add_to_list_view(self.items, self.item_list, "物品", dim_str)
                
            self.result_label.text = f"已添加 {c} 个物品（{int(w)}x{int(d)}x{int(h)}mm）"
            
        except ValueError:
            self.result_label.text = "[color=ff0000]错误：请输入有效的数字[/color]"

    def do_pack(self, instance):
        if not self.bins or not self.items:
            self.result_label.text = "[color=ff0000]错误：请先添加至少一个箱子和一个物品。[/color]"
            return
        
        # 优化3：提前体积校验，拦截物品尺寸大于箱子的无效计算
        max_item_w = max(it.width for it in self.items)
        max_item_d = max(it.depth for it in self.items)
        max_item_h = max(it.height for it in self.items)
        valid_bins = [b for b in self.bins if b.width>=max_item_w and b.depth>=max_item_d and b.height>=max_item_h]
        if not valid_bins:
            self.result_label.text = "[color=ff0000]错误：物品尺寸超过所有箱子，无法装箱！[/color]"
            return

        self.result_label.text = "计算中，请稍候..."
        self.packing_3d_view.packing_result = None
        self.packing_3d_view.redraw()
        # 后台线程执行计算
        thread = threading.Thread(target=self._pack_thread)
        thread.daemon = True
        thread.start()

    def _pack_thread(self):
        try:
            p = Packer()
            for b in self.bins:
                p.add_bin(b)
            for it in self.items:
                p.add_item(it)
            p.pack()
            # 准备3D显示数据
            self.packing_result_for_3d = []
            for idx, b in enumerate(p.bins):
                if b.items:
                    bin_info = {
                        'name': b.name,
                        'dims': (b.width, b.depth, b.height),
                        'color_idx': idx,
                        'items': []
                    }
                    for it in b.items:
                        item_info = {
                            'name': it.name,
                            'dims': (it.width, it.depth, it.height),
                            'position': (it.position[0], it.position[1], it.position[2])
                        }
                        bin_info['items'].append(item_info)
                    self.packing_result_for_3d.append(bin_info)
            # 主线程更新UI
            Clock.schedule_once(self._update_ui_after_pack)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._show_error(f"装箱计算失败：{str(e)}"))

    def _update_ui_after_pack(self, dt):
        """在主线程更新文本报告和3D视图"""
        if not self.packing_result_for_3d:
            self.result_label.text = (
                "[color=ff0000]计算完成，但未找到有效的装箱方案。\n"
                "可能原因：物品总体积过大或单件物品尺寸超过箱子。[/color]"
            )
            return
        # 更新文本报告
        result_text = "[b]智能装箱结果[/b]\n"
        total_items = sum(len(b['items']) for b in self.packing_result_for_3d)
        result_text += f"总计处理 {len(self.items)} 个物品，成功装入 {total_items} 个，使用 {len(self.packing_result_for_3d)} 个箱子。\n\n"
        for bin_data in self.packing_result_for_3d:
            w, d, h = bin_data['dims']
            v_total = w * d * h
            v_used = sum(it['dims'][0] * it['dims'][1] * it['dims'][2] 
                        for it in bin_data['items'])
            rate = v_used / v_total * 100 if v_total else 0
            
            result_text += f"[b]{bin_data['name']}[/b] ({int(w)}x{int(d)}x{int(h)}mm)\n"
            result_text += f"  装载数: {len(bin_data['items'])} | 体积利用率: {rate:.1f}%\n"
            result_text += "  物品明细:\n"
            for it in bin_data['items']:
                pos = it['position']
                result_text += f"    - {it['name']} 位置: ({pos[0]:.0f}, {pos[1]:.0f}, {pos[2]:.0f})\n"
            result_text += "\n"
        
        self.result_label.text = result_text
        # 更新3D视图
        self.packing_3d_view.packing_result = self.packing_result_for_3d
        self.packing_3d_view.redraw()

    def _show_error(self, msg):
        self.result_label.text = f"[color=ff0000]{msg}[/color]"

    def do_clear(self, instance):
        self.bins.clear()
        self.items.clear()
        self.bin_list.clear_widgets()
        self.item_list.clear_widgets()
        self.result_label.text = "[b]就绪[/b]\n所有数据已清空。"
        self.packing_result_for_3d = []
        self.packing_3d_view.packing_result = None
        self.packing_3d_view.redraw()

class PackApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.primary_hue = "500"
        # 优化：设置安卓窗口自适应
        Window.softinput_mode = "below_target"
        return Pack3DUI()

if __name__ == "__main__":
    PackApp().run()
