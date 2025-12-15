# -*- coding: utf-8 -*-
"""
图片处理工具 - 白色背景转透明
"""
import base64
import io
from PIL import Image
import numpy as np


def white_to_transparent(image_data: str, threshold: int = 245) -> str:
    """将PNG图片的白色背景转换为透明
    
    Args:
        image_data: Base64编码的PNG图片数据（可带data:image/png;base64,前缀）
        threshold: 白色阈值，RGB值都大于此值的像素会被设为透明（默认245，适合ECharts图表）
        
    Returns:
        Base64编码的透明背景PNG图片数据（带data:image/png;base64,前缀）
    """
    # 移除data URL前缀
    if ',' in image_data:
        image_data = image_data.split(',')[1]
    
    # 解码Base64
    image_bytes = base64.b64decode(image_data)
    
    # 打开图片
    img = Image.open(io.BytesIO(image_bytes))
    
    # 转换为RGBA模式
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # 转换为numpy数组
    data = np.array(img)
    
    # 找到白色/接近白色的像素（RGB都大于阈值）
    white_mask = (data[:, :, 0] > threshold) & \
                 (data[:, :, 1] > threshold) & \
                 (data[:, :, 2] > threshold)
    
    # 将白色像素的alpha通道设为0（透明）
    data[white_mask, 3] = 0
    
    # 创建新图片
    result = Image.fromarray(data, 'RGBA')
    
    # 保存到字节流
    output = io.BytesIO()
    result.save(output, format='PNG')
    output.seek(0)
    
    # 编码为Base64
    result_base64 = base64.b64encode(output.getvalue()).decode('utf-8')
    
    return f"data:image/png;base64,{result_base64}"


def process_chart_image(image_data: str) -> dict:
    """处理图表图片，返回透明背景版本
    
    Args:
        image_data: Base64编码的PNG图片数据
        
    Returns:
        包含处理结果的字典
    """
    try:
        transparent_image = white_to_transparent(image_data)
        return {
            'success': True,
            'image': transparent_image
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
