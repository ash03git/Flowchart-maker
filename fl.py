import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import math
from typing import List, Dict, Tuple, Optional

class FlowchartShape:
    def __init__(self, shape_type: str, x: int, y: int, width: int = 100, height: int = 50, text: str = ""):
        self.shape_type = shape_type
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.canvas_id = None
        self.text_id = None
        
    def to_dict(self):
        return {
            'shape_type': self.shape_type,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'text': self.text
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(data['shape_type'], data['x'], data['y'], 
                  data['width'], data['height'], data['text'])

class FlowchartArrow:
    def __init__(self, arrow_type: str, start_x: float, start_y: float, end_x: float, end_y: float):
        self.arrow_type = arrow_type  # 'straight', 'curved', 'dashed', 'double', 'bidirectional'
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y
        self.canvas_ids = []  # Multiple canvas items for complex arrows
        
    def to_dict(self):
        return {
            'arrow_type': self.arrow_type,
            'start_x': self.start_x,
            'start_y': self.start_y,
            'end_x': self.end_x,
            'end_y': self.end_y
        }
        
    @classmethod
    def from_dict(cls, data):
        return cls(data['arrow_type'], data['start_x'], data['start_y'], data['end_x'], data['end_y'])

class FlowchartMaker:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Flowchart Maker")
        self.root.geometry("1200x800")
        
        # Data structures
        self.shapes: List[FlowchartShape] = []
        self.arrows: List[FlowchartArrow] = []
        self.history: List[Dict] = []
        self.history_index = -1
        self.selected_shape = None
        
        # Drawing states
        self.drawing_shape = False
        self.drawing_arrow = False
        self.moving_shape = False
        self.start_x = 0
        self.start_y = 0
        self.current_x = 0
        self.current_y = 0
        self.temp_items = []  # For temporary drawing items
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Current mode
        self.current_shape_type = 'rectangle'
        self.current_arrow_type = 'straight'
        self.current_mode = 'select'  # 'select', 'draw_shape', 'draw_arrow'
        
        self.setup_ui()
        self.save_state()  # Initial state
        
    def setup_ui(self):
        # Create main container
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel for shapes and tools
        left_frame = ttk.Frame(main_container)
        main_container.add(left_frame, weight=0)
        
        # Right panel for canvas
        right_frame = ttk.Frame(main_container)
        main_container.add(right_frame, weight=1)
        
        self.setup_left_panel(left_frame)
        self.setup_canvas_area(right_frame)
        
    def setup_left_panel(self, parent):
        # Tools section
        tools_frame = ttk.LabelFrame(parent, text="Tools", padding=5)
        tools_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(tools_frame, text="Select/Move", command=lambda: self.set_mode('select')).pack(fill=tk.X, pady=2)
        ttk.Button(tools_frame, text="Add Text", command=self.add_text_to_selected).pack(fill=tk.X, pady=2)
        ttk.Button(tools_frame, text="Delete", command=self.delete_selected).pack(fill=tk.X, pady=2)
        
        # Shapes section - only essential shapes
        shapes_frame = ttk.LabelFrame(parent, text="Shapes", padding=5)
        shapes_frame.pack(fill=tk.X, padx=5, pady=5)
        
        essential_shapes = [
            ("Rectangle", "rectangle"),
            ("Oval/Circle", "oval"),
            ("Diamond", "diamond"),
            ("Triangle", "triangle"),
            ("Parallelogram", "parallelogram"),
            ("Hexagon", "hexagon"),
            ("Star", "star")
        ]
        
        for name, shape_type in essential_shapes:
            btn = ttk.Button(shapes_frame, text=name, 
                           command=lambda st=shape_type: self.set_shape_mode(st))
            btn.pack(fill=tk.X, pady=1)
            
        # Connectors section - different arrow types
        connectors_frame = ttk.LabelFrame(parent, text="Connectors", padding=5)
        connectors_frame.pack(fill=tk.X, padx=5, pady=5)
        
        arrow_types = [
            ("Straight Arrow", "straight"),
            ("Curved Arrow", "curved"),
            ("Dashed Arrow", "dashed"),
            ("Double Arrow", "double"),
            ("Bidirectional", "bidirectional"),
            ("Thick Arrow", "thick"),
            ("Dotted Line", "dotted")
        ]
        
        for name, arrow_type in arrow_types:
            btn = ttk.Button(connectors_frame, text=name,
                           command=lambda at=arrow_type: self.set_arrow_mode(at))
            btn.pack(fill=tk.X, pady=1)
        
        # History section - Undo/Redo
        history_frame = ttk.LabelFrame(parent, text="History", padding=5)
        history_frame.pack(fill=tk.X, padx=5, pady=5)
        
        undo_frame = ttk.Frame(history_frame)
        undo_frame.pack(fill=tk.X, pady=2)
        ttk.Button(undo_frame, text="Undo", command=self.undo).pack(side=tk.LEFT, padx=(0,2), fill=tk.X, expand=True)
        ttk.Button(undo_frame, text="Redo", command=self.redo).pack(side=tk.RIGHT, padx=(2,0), fill=tk.X, expand=True)
        
    def setup_canvas_area(self, parent):
        # Top bar with file operations and status
        top_bar = ttk.Frame(parent)
        top_bar.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        
        # Status bar on left
        self.status_var = tk.StringVar()
        self.status_var.set("Ready - Select a shape and drag on canvas to draw")
        status_bar = ttk.Label(top_bar, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # File operations on top right without label
        file_frame = ttk.Frame(top_bar)
        file_frame.pack(side=tk.RIGHT)
        
        ttk.Button(file_frame, text="New", command=self.clear_canvas).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="Open", command=self.load_file).pack(side=tk.LEFT, padx=2)
        
        # Canvas with scrollbars
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg='white', relief=tk.SUNKEN, bd=2)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.configure(xscrollcommand=h_scrollbar.set)
        
        # Set large scrollregion for drawing
        self.canvas.configure(scrollregion=(0, 0, 2000, 2000))
        
        # Bind canvas events
        self.canvas.bind("<Button-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Motion>", self.on_canvas_motion)
        
    def set_mode(self, mode):
        self.current_mode = mode
        if mode == 'select':
            self.status_var.set("Select mode - Click shapes to select, drag to move")
        self.canvas.configure(cursor="arrow" if mode == 'select' else "crosshair")
        
    def set_shape_mode(self, shape_type):
        self.current_shape_type = shape_type
        self.current_mode = 'draw_shape'
        self.status_var.set(f"Draw mode - Drag to create {shape_type}")
        self.canvas.configure(cursor="crosshair")
        
    def set_arrow_mode(self, arrow_type):
        self.current_arrow_type = arrow_type
        self.current_mode = 'draw_arrow'
        self.status_var.set(f"Connector mode - Drag to create {arrow_type}")
        self.canvas.configure(cursor="crosshair")
        
    def on_canvas_press(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.start_x, self.start_y = x, y
        
        if self.current_mode == 'select':
            clicked_shape = self.get_shape_at_position(x, y)
            if clicked_shape:
                self.select_shape(clicked_shape)
                self.moving_shape = True
                self.drag_start_x = x - clicked_shape.x
                self.drag_start_y = y - clicked_shape.y
            else:
                self.deselect_all()
                
        elif self.current_mode == 'draw_shape':
            self.drawing_shape = True
            self.temp_items = [self.draw_temp_shape(x, y, x, y)]
            
        elif self.current_mode == 'draw_arrow':
            self.drawing_arrow = True
            self.temp_items = self.draw_temp_arrow(x, y, x, y)
            
    def on_canvas_drag(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.current_x, self.current_y = x, y
        
        if self.moving_shape and self.selected_shape:
            new_x = x - self.drag_start_x
            new_y = y - self.drag_start_y
            self.selected_shape.x = new_x
            self.selected_shape.y = new_y
            self.redraw_canvas()
            
        elif self.drawing_shape and self.temp_items:
            for item in self.temp_items:
                self.canvas.delete(item)
            self.temp_items = [self.draw_temp_shape(self.start_x, self.start_y, x, y)]
            
        elif self.drawing_arrow and self.temp_items:
            for item in self.temp_items:
                self.canvas.delete(item)
            self.temp_items = self.draw_temp_arrow(self.start_x, self.start_y, x, y)
            
    def on_canvas_release(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        if self.moving_shape:
            self.moving_shape = False
            if self.selected_shape:
                self.save_state()
                
        elif self.drawing_shape:
            self.drawing_shape = False
            for item in self.temp_items:
                self.canvas.delete(item)
            self.create_shape_from_drag(self.start_x, self.start_y, x, y)
                
        elif self.drawing_arrow:
            self.drawing_arrow = False
            for item in self.temp_items:
                self.canvas.delete(item)
            self.create_arrow_from_drag(self.start_x, self.start_y, x, y)
                
        self.temp_items = []
        
    def on_canvas_motion(self, event):
        pass
        
    def on_double_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        shape = self.get_shape_at_position(x, y)
        if shape:
            self.edit_text(shape)
            
    def draw_temp_shape(self, x1, y1, x2, y2):
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        
        if right - left < 20:
            right = left + 20
        if bottom - top < 20:
            bottom = top + 20
            
        return self.draw_shape_on_canvas(self.current_shape_type, left, top, right - left, bottom - top, temp=True)
        
    def draw_temp_arrow(self, x1, y1, x2, y2):
        return self.draw_arrow_on_canvas(self.current_arrow_type, x1, y1, x2, y2, temp=True)
        
    def create_shape_from_drag(self, x1, y1, x2, y2):
        left = min(x1, x2)
        top = min(y1, y2)
        width = max(abs(x2 - x1), 50)
        height = max(abs(y2 - y1), 30)
        
        shape = FlowchartShape(self.current_shape_type, left, top, width, height)
        self.shapes.append(shape)
        self.redraw_canvas()
        self.save_state()
        self.status_var.set(f"{self.current_shape_type} created")
        
    def create_arrow_from_drag(self, x1, y1, x2, y2):
        if abs(x2 - x1) > 10 or abs(y2 - y1) > 10:
            arrow = FlowchartArrow(self.current_arrow_type, x1, y1, x2, y2)
            self.arrows.append(arrow)
            self.redraw_canvas()
            self.save_state()
            self.status_var.set(f"{self.current_arrow_type} arrow created")
            
    def draw_shape_on_canvas(self, shape_type, x, y, width, height, temp=False):
        fill_color = 'lightgray' if temp else 'white'
        outline_color = 'gray' if temp else 'black'
        outline_width = 1 if temp else 2
        
        x1, y1, x2, y2 = x, y, x + width, y + height
        center_x, center_y = x + width/2, y + height/2
        
        if shape_type == 'rectangle':
            return self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline=outline_color, width=outline_width)
            
        elif shape_type == 'oval':
            return self.canvas.create_oval(x1, y1, x2, y2, fill=fill_color, outline=outline_color, width=outline_width)
            
        elif shape_type == 'diamond':
            points = [center_x, y1, x2, center_y, center_x, y2, x1, center_y]
            return self.canvas.create_polygon(points, fill=fill_color, outline=outline_color, width=outline_width)
            
        elif shape_type == 'triangle':
            points = [center_x, y1, x2, y2, x1, y2]
            return self.canvas.create_polygon(points, fill=fill_color, outline=outline_color, width=outline_width)
            
        elif shape_type == 'parallelogram':
            offset = width // 4
            points = [x1 + offset, y1, x2, y1, x2 - offset, y2, x1, y2]
            return self.canvas.create_polygon(points, fill=fill_color, outline=outline_color, width=outline_width)
            
        elif shape_type == 'hexagon':
            w_third = width // 3
            points = [x1 + w_third, y1, x2 - w_third, y1, x2, center_y, x2 - w_third, y2, x1 + w_third, y2, x1, center_y]
            return self.canvas.create_polygon(points, fill=fill_color, outline=outline_color, width=outline_width)
            
        elif shape_type == 'star':
            points = []
            for i in range(10):
                angle = i * math.pi / 5 - math.pi/2
                if i % 2 == 0:
                    px = center_x + (width/2) * math.cos(angle)
                    py = center_y + (height/2) * math.sin(angle)
                else:
                    px = center_x + (width/4) * math.cos(angle)
                    py = center_y + (height/4) * math.sin(angle)
                points.extend([px, py])
            return self.canvas.create_polygon(points, fill=fill_color, outline=outline_color, width=outline_width)
            
        else:
            return self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline=outline_color, width=outline_width)
            
    def draw_arrow_on_canvas(self, arrow_type, x1, y1, x2, y2, temp=False):
        color = 'gray' if temp else 'black'
        width = 1 if temp else 2
        items = []
        
        if arrow_type == 'straight':
            items.append(self.canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, width=width, fill=color))
            
        elif arrow_type == 'curved':
            # Create a curved arrow using multiple line segments
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            # Add curve offset
            offset = 30
            curve_x = mid_x + offset if (x2 - x1) * (y2 - y1) > 0 else mid_x - offset
            curve_y = mid_y - offset if y2 > y1 else mid_y + offset
            
            # Draw curved line using smooth curve approximation
            points = [x1, y1]
            for t in [0.2, 0.4, 0.6, 0.8, 1.0]:
                # Quadratic Bezier curve
                px = (1-t)**2 * x1 + 2*(1-t)*t * curve_x + t**2 * x2
                py = (1-t)**2 * y1 + 2*(1-t)*t * curve_y + t**2 * y2
                points.extend([px, py])
            items.append(self.canvas.create_line(points, smooth=True, arrow=tk.LAST, width=width, fill=color))
            
        elif arrow_type == 'dashed':
            items.append(self.canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, width=width, fill=color, dash=(5, 5)))
            
        elif arrow_type == 'double':
            # Draw two parallel lines
            dx, dy = x2 - x1, y2 - y1
            length = math.sqrt(dx**2 + dy**2)
            if length > 0:
                offset_x = -dy / length * 3  # Perpendicular offset
                offset_y = dx / length * 3
                items.append(self.canvas.create_line(x1 + offset_x, y1 + offset_y, x2 + offset_x, y2 + offset_y, 
                                                   arrow=tk.LAST, width=width, fill=color))
                items.append(self.canvas.create_line(x1 - offset_x, y1 - offset_y, x2 - offset_x, y2 - offset_y, 
                                                   arrow=tk.LAST, width=width, fill=color))
            
        elif arrow_type == 'bidirectional':
            items.append(self.canvas.create_line(x1, y1, x2, y2, arrow=tk.BOTH, width=width, fill=color))
            
        elif arrow_type == 'thick':
            items.append(self.canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, width=width*2, fill=color))
            
        elif arrow_type == 'dotted':
            items.append(self.canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, width=width, fill=color, dash=(2, 3)))
            
        return items
            
    def draw_shape(self, shape: FlowchartShape):
        fill_color = 'lightblue' if shape == self.selected_shape else 'white'
        outline_color = 'blue' if shape == self.selected_shape else 'black'
        outline_width = 2 if shape == self.selected_shape else 1
        
        # Draw shape
        shape.canvas_id = self.draw_shape_on_canvas(shape.shape_type, shape.x, shape.y, shape.width, shape.height)
        
        # Update colors for selection
        if shape == self.selected_shape:
            self.canvas.itemconfig(shape.canvas_id, fill='lightblue', outline='blue', width=2)
        
        # Draw text
        if shape.text:
            center_x = shape.x + shape.width / 2
            center_y = shape.y + shape.height / 2
            shape.text_id = self.canvas.create_text(
                center_x, center_y, text=shape.text, font=('Arial', 10), anchor='center')
                
    def draw_arrow(self, arrow: FlowchartArrow):
        arrow.canvas_ids = self.draw_arrow_on_canvas(arrow.arrow_type, arrow.start_x, arrow.start_y, arrow.end_x, arrow.end_y)
            
    def get_shape_at_position(self, x, y) -> Optional[FlowchartShape]:
        for shape in reversed(self.shapes):
            if (shape.x <= x <= shape.x + shape.width and 
                shape.y <= y <= shape.y + shape.height):
                return shape
        return None
        
    def select_shape(self, shape):
        self.selected_shape = shape
        self.redraw_canvas()
        
    def deselect_all(self):
        self.selected_shape = None
        self.redraw_canvas()
        
    def redraw_canvas(self):
        self.canvas.delete("all")
        
        # Draw all shapes
        for shape in self.shapes:
            self.draw_shape(shape)
            
        # Draw all arrows
        for arrow in self.arrows:
            self.draw_arrow(arrow)
            
    def add_text_to_selected(self):
        if not self.selected_shape:
            messagebox.showwarning("No Selection", "Please select a shape first")
            return
        self.edit_text(self.selected_shape)
        
    def edit_text(self, shape: FlowchartShape):
        current_text = shape.text if shape.text else ""
        new_text = simpledialog.askstring("Edit Text", "Enter text for shape:", initialvalue=current_text)
        
        if new_text is not None:
            shape.text = new_text
            self.redraw_canvas()
            self.save_state()
            
    def delete_selected(self):
        if not self.selected_shape:
            messagebox.showwarning("No Selection", "Please select a shape first")
            return
            
        self.shapes.remove(self.selected_shape)
        self.selected_shape = None
        self.redraw_canvas()
        self.save_state()
        self.status_var.set("Shape deleted")
        
    def save_state(self):
        state = {
            'shapes': [shape.to_dict() for shape in self.shapes],
            'arrows': [arrow.to_dict() for arrow in self.arrows]
        }
        
        # Remove future history if we're not at the end
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
            
        self.history.append(state)
        self.history_index += 1
        
        # Limit history size
        if len(self.history) > 50:
            self.history.pop(0)
            self.history_index -= 1
            
    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.restore_state(self.history[self.history_index])
            self.status_var.set("Undone")
        else:
            self.status_var.set("Nothing to undo")
            
    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.restore_state(self.history[self.history_index])
            self.status_var.set("Redone")
        else:
            self.status_var.set("Nothing to redo")
            
    def restore_state(self, state):
        # Clear current state
        self.shapes.clear()
        self.arrows.clear()
        self.selected_shape = None
        
        # Restore shapes
        for shape_data in state['shapes']:
            shape = FlowchartShape.from_dict(shape_data)
            self.shapes.append(shape)
            
        # Restore arrows
        for arrow_data in state['arrows']:
            arrow = FlowchartArrow.from_dict(arrow_data)
            self.arrows.append(arrow)
            
        self.redraw_canvas()
        
    def save_file(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                data = {
                    'shapes': [shape.to_dict() for shape in self.shapes],
                    'arrows': [arrow.to_dict() for arrow in self.arrows]
                }
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                    
                self.status_var.set(f"Saved to {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
                
    def load_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                    
                self.clear_canvas(confirm=False)
                
                for shape_data in data['shapes']:
                    shape = FlowchartShape.from_dict(shape_data)
                    self.shapes.append(shape)
                    
                for arrow_data in data['arrows']:
                    arrow = FlowchartArrow.from_dict(arrow_data)
                    self.arrows.append(arrow)
                        
                self.redraw_canvas()
                self.save_state()
                self.status_var.set(f"Loaded from {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")
                
    def clear_canvas(self, confirm=True):
        if not confirm or not (self.shapes or self.arrows) or messagebox.askyesno("Clear Canvas", "Are you sure you want to clear everything?"):
            self.shapes.clear()
            self.arrows.clear()
            self.selected_shape = None
            self.redraw_canvas()
            self.save_state()
            self.status_var.set("Canvas cleared")

def main():
    root = tk.Tk()
    app = FlowchartMaker(root)
    root.mainloop()

if __name__ == "__main__":
    main()