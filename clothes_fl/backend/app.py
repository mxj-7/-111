from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
import shutil
import sqlite3
from datetime import datetime
import base64
import requests
import json
from urllib.parse import urljoin

app = FastAPI()

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路径配置
DB_PATH = os.path.join(os.path.dirname(__file__), '../db/clothes.db')
IMAGE_DIR = os.path.join(os.path.dirname(__file__), '../images')

# Coze API配置
COZE_API_TOKEN = "pat_lAur3A7n5h4DoXRkKW2JiePWYXJh0SGRGepbXABXzGHvLyJrjTaxwlFUS3CDMFTD"
COZE_BASE_URL = "https://api.coze.cn"
WORKFLOW_ID = "7529911699437748278"

# 数据库初始化
def init_database():
    """初始化数据库"""
    # 如果表结构有变动，建议自动删除旧数据库（开发环境下安全）
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT style FROM clothes LIMIT 1')
            conn.close()
        except Exception:
            os.remove(DB_PATH)
    
    # 创建数据库目录和表
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clothes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        upload_time TEXT,
        style TEXT,
        color TEXT,
        tone TEXT,
        collar TEXT,
        sleeve TEXT,
        shape TEXT,
        length TEXT,
        fabric TEXT,
        pattern TEXT,
        craft TEXT,
        occasion TEXT,
        season TEXT,
        style_type TEXT,
        ai_tags TEXT,
        confidence REAL
    )''')
    conn.commit()
    conn.close()

# 启动时初始化数据库
init_database()

def parse_ai_tags(ai_output):
    """解析AI返回的标签信息，并与标签库进行匹配验证"""
    try:
        print(f"🔍 开始解析AI输出: {ai_output}")
        
        # 确保转换为字符串
        if isinstance(ai_output, str):
            result_text = ai_output
        else:
            result_text = str(ai_output)
        
        # 定义标签库
        TAG_LIBRARY = {
            "style": ["衬衫", "T恤", "连衣裙", "裤子", "裙子", "外套", "毛衣"],
            "color": ["红色", "蓝色", "白色", "黑色", "灰色", "绿色", "黄色", "紫色", "粉色", "棕色"],
            "tone": ["浅色调", "深色调", "中性色调", "亮色调"],
            "collar": ["圆领", "V领", "高领", "翻领", "立领", "一字领", "方领", "心形领", "无领"],
            "sleeve": ["长袖", "短袖", "无袖", "七分袖", "五分袖", "泡泡袖", "喇叭袖", "紧身袖"],
            "shape": ["修身", "宽松", "直筒", "A字型", "H型", "X型", "合身"],
            "length": ["超短", "短款", "中长款", "长款", "及膝", "及踝"],
            "fabric": ["棉质", "丝质", "麻质", "毛料", "化纤", "混纺", "牛仔", "皮革", "针织"],
            "pattern": ["纯色", "条纹", "格子", "印花", "刺绣", "蕾丝", "网纱"],
            "craft": ["拼接", "褶皱", "抽绳", "拉链", "纽扣", "系带", "无"],
            "occasion": ["休闲", "正式", "运动", "居家", "派对", "职场", "度假", "万圣节"],
            "season": ["春季", "夏季", "秋季", "冬季", "四季通用", "秋冬", "春夏"],
            "style_type": ["简约", "复古", "甜美", "帅气", "优雅", "个性", "时尚", "可爱"]
        }
        
        # 字段映射（API字段名 -> 数据库字段名）
        FIELD_MAPPING = {
            "样式名称": "style", "样式": "style", "类型": "style",
            "颜色": "color", "主色调": "color",
            "色调": "tone", "色彩": "tone",
            "领": "collar", "领型": "collar", "领子": "collar",
            "袖": "sleeve", "袖型": "sleeve", "袖子": "sleeve",
            "版型": "shape", "形状": "shape", "轮廓": "shape",
            "长度": "length", "衣长": "length",
            "面料": "fabric", "材质": "fabric", "材料": "fabric",
            "图案": "pattern", "花纹": "pattern", "纹理": "pattern",
            "工艺": "craft", "制作工艺": "craft",
            "场合": "occasion", "适用场合": "occasion",
            "季节": "season", "适用季节": "season",
            "风格": "style_type", "服装风格": "style_type"
        }
        
        def validate_tag(field_name, tag_value):
            """验证标签是否在标签库中"""
            print(f"🔍 验证标签: field_name='{field_name}', tag_value='{tag_value}'")
            print(f"🔍 tag_value长度: {len(tag_value)}, 字节表示: {tag_value.encode('utf-8')}")
            
            if field_name in TAG_LIBRARY:
                print(f"🔍 标签库中的{field_name}选项: {TAG_LIBRARY[field_name]}")
                
                # 增强清理标签值（去除所有空格和不可见字符）
                clean_tag_value = tag_value.strip().replace(' ', '').replace('\u200b', '').replace('\ufeff', '')
                print(f"🔍 清理后的标签值: '{clean_tag_value}'")
                
                # 精确匹配
                for valid_tag in TAG_LIBRARY[field_name]:
                    print(f"🔍 比较: '{clean_tag_value}' == '{valid_tag}' ? {clean_tag_value == valid_tag}")
                    if clean_tag_value == valid_tag:
                        print(f"✅ 精确匹配成功: {clean_tag_value}")
                        return valid_tag
                
                # 模糊匹配（包含关系）
                for valid_tag in TAG_LIBRARY[field_name]:
                    if clean_tag_value in valid_tag or valid_tag in clean_tag_value:
                        print(f"✅ 模糊匹配成功: {clean_tag_value} <-> {valid_tag}")
                        return valid_tag
                        
                print(f"❌ 未找到匹配的标签: '{clean_tag_value}'")
            else:
                print(f"❌ 字段名不在标签库中: '{field_name}'")
                
            return "未识别"
        
        tags = {}
        
        # 使用正则表达式分割不同维度的标签
        import re
        
        # 匹配 "key：value" 格式的正则表达式
        
        # 改进的正则表达式，先清理JSON格式
        if ai_output.startswith('{"output":"'):
            start_idx = ai_output.find('"output":"') + len('"output":"')
            end_idx = ai_output.rfind('"}')
            if end_idx == -1:
                end_idx = len(ai_output)
            ai_output = ai_output[start_idx:end_idx]
            print(f"🔍 清理后的AI输出: {ai_output}")
        
        # 修复正则表达式 - 同时支持中文和英文冒号
        pattern = r'([^：:,，]+?)[:：]([^,，]+?)(?=[,，]|$)'
        matches = re.findall(pattern, ai_output)
        print(f"🔍 正则匹配结果: {matches}")
        
        # 如果正则匹配失败，使用分割方法作为备选
        if not matches:
            print("🔍 正则匹配失败，使用分割方法")
            # 先按中文逗号分割，再按英文逗号分割
            parts = ai_output.replace('，', ',').split(',')
            matches = []
            for part in parts:
                part = part.strip()
                # 同时支持中文和英文冒号
                if '：' in part:
                    key, value = part.split('：', 1)
                    matches.append((key.strip(), value.strip()))
                elif ':' in part:
                    key, value = part.split(':', 1)
                    matches.append((key.strip(), value.strip()))
            print(f"🔍 分割方法匹配结果: {matches}")
        
        for key, value in matches:
            key = key.strip()
            value = value.strip()
            
            print(f"🔍 处理维度: {key} = {value}")
            
            # 映射到数据库字段
            if key in FIELD_MAPPING:
                db_field = FIELD_MAPPING[key]
                # 与标签库进行匹配验证
                validated_tag = validate_tag(db_field, value)
                tags[db_field] = validated_tag
                
                if validated_tag == "未识别":
                    print(f"⚠️ 标签不在库中: {key}({db_field}) = {value} -> 未识别")
                else:
                    print(f"✅ 标签匹配成功: {key}({db_field}) = {value} -> {validated_tag}")
            else:
                print(f"⚠️ 未识别的维度: {key} = {value}")
        
        # 如果没有匹配到任何标签，尝试备用解析方法
        if not tags and "：" in result_text:
            print("🔍 使用备用解析方法")
            pairs = result_text.replace("，", ",").split(",")
            for pair in pairs:
                pair = pair.strip()
                if "：" in pair:
                    key, value = pair.split("：", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key in FIELD_MAPPING:
                        db_field = FIELD_MAPPING[key]
                        validated_tag = validate_tag(db_field, value)
                        tags[db_field] = validated_tag
        
        print(f"✅ 最终解析结果: {tags}")
        return tags if tags else None
        
    except Exception as e:
        print(f"❌ 解析AI标签出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def upload_image_to_postimage(image_path):
    """将图片上传到PostImage获取公网URL"""
    try:
        with open(image_path, 'rb') as file:
            files = {'upload': file}
            data = {
                'adult': 'no',
                'optsize': '0',
                'expire': '0'
            }
            
            response = requests.post(
                'https://postimages.org/json/rr',
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'OK':
                    return result.get('url')
            
            print(f"PostImage上传失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"上传图片到PostImage出错: {e}")
        return None

def call_coze_workflow(image_url):
    """调用Coze工作流进行图片标签识别"""
    headers = {
        "Authorization": f"Bearer {COZE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 修改payload，直接传递图片URL
    payload = {
        "workflow_id": WORKFLOW_ID,
        "parameters": {
            "image_url": image_url  # 直接传递图片URL
        }
    }
    
    try:
        response = requests.post(
            f"{COZE_BASE_URL}/v1/workflow/run",  # 使用非流式接口
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            # 根据实际返回结构解析结果
            if 'data' in result and 'output' in result['data']:
                return parse_ai_tags(result['data']['output'])
            else:
                print(f"Coze工作流返回格式异常: {result}")
                return None
        else:
            print(f"Coze API调用失败: {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        print(f"调用Coze API出错: {e}")
        return None

# 同时优化图片上传函数，确保能获取到可靠的公网URL
def upload_image_to_imgbb(image_path):
    """将图片上传到ImgBB获取公网URL"""
    api_key = "de720af6f7edfbb920da697cb6d6a2c9"  # 使用你的真实API密钥
    
    try:
        with open(image_path, 'rb') as file:
            image_data = base64.b64encode(file.read()).decode('utf-8')
            
        payload = {
            'key': api_key,
            'image': image_data,
            'expiration': 600  # 10分钟过期
        }
        
        response = requests.post(
            'https://api.imgbb.com/1/upload',
            data=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"ImgBB上传成功: {result['data']['url']}")
                return result['data']['url']
        
        print(f"ImgBB上传失败: {response.text}")
        return None
        
    except Exception as e:
        print(f"上传图片到ImgBB出错: {e}")
        return None

def upload_image_to_coze(image_path):
    """将图片上传到Coze平台获取file_id"""
    headers = {
        "Authorization": f"Bearer {COZE_API_TOKEN}"
    }
    
    try:
        with open(image_path, 'rb') as file:
            files = {'file': file}
            response = requests.post(
                f"{COZE_BASE_URL}/v1/files/upload",
                headers=headers,
                files=files,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                file_id = result.get('data', {}).get('id')
                print(f"✅ Coze文件上传成功，file_id: {file_id}")
                return file_id
            else:
                print(f"❌ Coze文件上传失败: {response.status_code}, {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ 上传图片到Coze出错: {e}")
        return None

def call_coze_workflow(file_id):
    """调用Coze工作流进行图片标签识别"""
    headers = {
        "Authorization": f"Bearer {COZE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "workflow_id": WORKFLOW_ID,
        "parameters": {
            "input": json.dumps({"file_id": file_id})
        }
    }
    
    try:
        response = requests.post(
            f"{COZE_BASE_URL}/v1/workflow/run",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Coze工作流调用成功: {result}")
            
            # 修复：直接使用result['data']作为字符串
            if 'data' in result:
                output_data = result['data']
                print(f"🔍 提取到的输出数据: {output_data}")
                print(f"🔍 数据类型: {type(output_data)}")
                
                # 直接传递给解析函数
                parsed_result = parse_ai_tags(output_data)
                print(f"🔍 解析结果: {parsed_result}")
                return parsed_result
            else:
                print(f"⚠️ Coze工作流返回格式异常: {result}")
                return None
        else:
            print(f"❌ Coze API调用失败: {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 调用Coze API出错: {e}")
        return None

@app.post("/upload/")
def upload_image(file: UploadFile = File(...)):
    """上传图片并进行AI标签识别"""
    try:
        # 保存图片到本地
        os.makedirs(IMAGE_DIR, exist_ok=True)
        file_path = os.path.join(IMAGE_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 方法1: 直接上传到Coze平台
        print(f"🔄 正在上传图片到Coze平台: {file.filename}")
        coze_file_id = upload_image_to_coze(file_path)
        
        ai_tags = None
        parsed_tags = {}
        if coze_file_id:
            # 调用Coze工作流进行标签识别
            print(f"🔄 正在调用Coze工作流，file_id: {coze_file_id}")
            
            # 直接调用Coze API，避免函数重复定义冲突
            headers = {
                "Authorization": f"Bearer {COZE_API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "workflow_id": WORKFLOW_ID,
                "parameters": {
                    "input": json.dumps({"file_id": coze_file_id})
                }
            }
            
            try:
                response = requests.post(
                    f"{COZE_BASE_URL}/v1/workflow/run",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Coze工作流调用成功: {result}")
                    
                    if 'data' in result:
                        output_data = result['data']
                        print(f"🔍 提取到的输出数据: {output_data}")
                        print(f"🔍 数据类型: {type(output_data)}")
                        
                        # 直接调用parse_ai_tags解析（只解析一次）
                        parsed_tags = parse_ai_tags(output_data)
                        ai_tags = output_data  # 保存原始数据
                        print(f"✅ AI标签解析成功: {parsed_tags}")
                    else:
                        print(f"⚠️ Coze工作流返回格式异常: {result}")
                        parsed_tags = {}
                else:
                    print(f"❌ Coze API调用失败: {response.status_code}, {response.text}")
                    parsed_tags = {}
                    
            except Exception as e:
                print(f"❌ 调用Coze API出错: {e}")
                parsed_tags = {}
        else:
            print("❌ 无法获取Coze file_id，跳过AI标签识别")
            parsed_tags = {}
        
        # 获取公网URL用于前端显示
        public_image_url = upload_image_to_imgbb(file_path)
        if not public_image_url:
            public_image_url = f"http://localhost:8000/imagefile/{file.filename}"
        
        # 保存到数据库
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 从AI标签中提取各个字段，如果没有则使用默认值
        style = parsed_tags.get('style', '未知')
        color = parsed_tags.get('color', '未知')
        tone = parsed_tags.get('tone', '未知')
        collar = parsed_tags.get('collar', '未知')
        sleeve = parsed_tags.get('sleeve', '未知')
        shape = parsed_tags.get('shape', '未知')
        length = parsed_tags.get('length', '未知')
        fabric = parsed_tags.get('fabric', '未知')
        pattern = parsed_tags.get('pattern', '未知')
        craft = parsed_tags.get('craft', '未知')
        occasion = parsed_tags.get('occasion', '未知')
        season = parsed_tags.get('season', '未知')
        style_type = parsed_tags.get('style_type', '未知')
        confidence = parsed_tags.get('confidence', 0.0)
        
        # 将原始AI标签结果也保存
        ai_tags_str = str(ai_tags) if ai_tags else "AI标签识别失败"
        
        # 修复后的SQL语句 - 参数数量匹配
        c.execute("""
            INSERT INTO clothes (filename, upload_time, style, color, tone, collar, sleeve, shape, length, fabric, pattern, craft, occasion, season, style_type, ai_tags, confidence)
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (file.filename, style, color, tone, collar, sleeve, shape, length, fabric, pattern, craft, occasion, season, style_type, ai_tags_str, confidence))
        
        image_id = c.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ 图片已保存到数据库，ID: {image_id}")
        
        return {
            "msg": "上传成功", 
            "id": image_id,
            "filename": file.filename,
            "public_url": public_image_url,
            "coze_file_id": coze_file_id,
            "ai_tags": ai_tags_str,
            "parsed_tags": parsed_tags
        }
        
    except Exception as e:
        print(f"❌ 上传图片时发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@app.get("/images/")
def list_images():
    """获取所有图片列表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, filename, upload_time, style, color, tone, collar, sleeve, shape, length, fabric, pattern, craft, occasion, season, style_type, ai_tags, confidence FROM clothes ORDER BY upload_time DESC")
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": row[0], "filename": row[1], "upload_time": row[2], 
            "style": row[3], "color": row[4], "tone": row[5], 
            "collar": row[6], "sleeve": row[7], "shape": row[8], 
            "length": row[9], "fabric": row[10], "pattern": row[11], 
            "craft": row[12], "occasion": row[13], "season": row[14], 
            "style_type": row[15], "ai_tags": row[16], "confidence": row[17]
        }
        for row in rows
    ]

@app.get("/image/{image_id}")
def get_image_detail(image_id: int):
    """获取单个图片详情"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, filename, upload_time, style, color, tone, collar, sleeve, shape, length, fabric, pattern, craft, occasion, season, style_type, ai_tags, confidence FROM clothes WHERE id=?", (image_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="图片不存在")
    return {
        "id": row[0], "filename": row[1], "upload_time": row[2], 
        "style": row[3], "color": row[4], "tone": row[5], 
        "collar": row[6], "sleeve": row[7], "shape": row[8], 
        "length": row[9], "fabric": row[10], "pattern": row[11], 
        "craft": row[12], "occasion": row[13], "season": row[14], 
        "style_type": row[15], "ai_tags": row[16], "confidence": row[17]
    }

@app.get("/imagefile/{filename}")
def get_image_file(filename: str):
    """获取图片文件"""
    file_path = os.path.join(IMAGE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="图片文件不存在")
    return FileResponse(file_path)

@app.post("/edit_tags/{image_id}")
def edit_tags(
    image_id: int,
    style: str = Form(None),
    color: str = Form(None),
    tone: str = Form(None),
    collar: str = Form(None),
    sleeve: str = Form(None),
    shape: str = Form(None),
    length: str = Form(None),
    fabric: str = Form(None),
    pattern: str = Form(None),
    craft: str = Form(None),
    occasion: str = Form(None),
    season: str = Form(None),
    style_type: str = Form(None)
):
    """编辑图片标签"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE clothes SET style=?, color=?, tone=?, collar=?, sleeve=?, shape=?, length=?, fabric=?, pattern=?, craft=?, occasion=?, season=?, style_type=? WHERE id=?
    """, (style, color, tone, collar, sleeve, shape, length, fabric, pattern, craft, occasion, season, style_type, image_id))
    conn.commit()
    conn.close()
    return {"msg": "标签已更新"}

@app.post("/delete/{image_id}")
def delete_image(image_id: int):
    """删除图片"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT filename FROM clothes WHERE id=?", (image_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="图片不存在")
    filename = row[0]
    c.execute("DELETE FROM clothes WHERE id=?", (image_id,))
    conn.commit()
    conn.close()
    
    # 删除图片文件
    file_path = os.path.join(IMAGE_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return {"msg": "图片已删除"}

@app.get("/search/")
def search_images(q: Optional[str] = None, tags: Optional[str] = None):
    """搜索图片"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    sql = "SELECT id, filename, upload_time, style, color, tone, collar, sleeve, shape, length, fabric, pattern, craft, occasion, season, style_type, ai_tags, confidence FROM clothes WHERE 1=1"
    params = []
    
    if q:
        sql += " AND (filename LIKE ? OR style LIKE ? OR color LIKE ? OR tone LIKE ? OR collar LIKE ? OR sleeve LIKE ? OR shape LIKE ? OR length LIKE ? OR fabric LIKE ? OR pattern LIKE ? OR craft LIKE ? OR occasion LIKE ? OR season LIKE ? OR style_type LIKE ? OR ai_tags LIKE ?)"
        params += [f"%{q}%"] * 15
    
    if tags:
        for tag in tags.split(","):
            sql += " AND (style LIKE ? OR color LIKE ? OR tone LIKE ? OR collar LIKE ? OR sleeve LIKE ? OR shape LIKE ? OR length LIKE ? OR fabric LIKE ? OR pattern LIKE ? OR craft LIKE ? OR occasion LIKE ? OR season LIKE ? OR style_type LIKE ? OR ai_tags LIKE ?)"
            params += [f"%{tag.strip()}%"] * 14
    
    sql += " ORDER BY upload_time DESC"
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    
    return [
        {
            "id": row[0], "filename": row[1], "upload_time": row[2], 
            "style": row[3], "color": row[4], "tone": row[5], 
            "collar": row[6], "sleeve": row[7], "shape": row[8], 
            "length": row[9], "fabric": row[10], "pattern": row[11], 
            "craft": row[12], "occasion": row[13], "season": row[14], 
            "style_type": row[15], "ai_tags": row[16], "confidence": row[17]
        }
        for row in rows
    ]

@app.post("/search_by_image/")
def search_by_image(file: UploadFile = File(...)):
    """以图搜图功能（预留）"""
    return {"msg": "以图搜图功能待实现"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)