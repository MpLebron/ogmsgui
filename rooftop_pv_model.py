import os
import rasterio
import geopandas as gpd
import numpy as np
from datetime import datetime
import glob

class RoofPVCarbonModel:
    """屋顶光伏碳减排潜力评估模型"""
    
    def __init__(self, radiation_folder="2018tif", system_efficiency=0.8, pv_efficiency=0.2):
        """
        初始化模型
        Args:
            radiation_folder: 存放太阳辐射tif文件的文件夹路径
            system_efficiency: 光伏系统综合效率，默认0.8
            pv_efficiency: 光伏转换效率，默认0.2
        """
        self.radiation_folder = radiation_folder
        self.system_efficiency = system_efficiency
        self.pv_efficiency = pv_efficiency

    def evaluate(self, 
                roof_vector_path,    # 屋顶矢量数据路径
                emission_factor,     # 电网碳排放因子
                start_time,         # 开始时间 'YYYY-MM'
                end_time,           # 结束时间 'YYYY-MM'
                time_scale='year',  # 'month' 或 'year'
                pv_efficiency=None): # 可选，覆盖默认光伏转换效率
        """
        评估��定区域的碳减排潜力
        """
        try:
            # 使用传入的效率值或默认值
            pv_efficiency = pv_efficiency or self.pv_efficiency
            
            # 1. 计算屋顶面积
            roof_area = self._calculate_roof_area(roof_vector_path)
            
            # 2. 获取研究区域范围
            bounds = self._get_study_area_bounds(roof_vector_path)
            
            # 3. 计算太阳辐射量
            radiation = self._calculate_radiation(bounds, start_time, end_time, time_scale)
            
            # 4. 计算碳减排量
            carbon_reduction = (roof_area * 
                              pv_efficiency * 
                              radiation * 
                              self.system_efficiency * 
                              emission_factor)
            
            # 5. 准备返回结果
            result = {
                'carbon_reduction': carbon_reduction,  # 单位：吨CO2
                'power_generation': carbon_reduction / emission_factor,  # 单位：kWh
                'parameters': {
                    'roof_area': roof_area,  # 单位：m2
                    'average_radiation': radiation,  # 单位：kWh/m2
                    'time_range': f"{start_time} to {end_time}",
                    'pv_efficiency': pv_efficiency,
                    'emission_factor': emission_factor
                }
            }
            
            return result
            
        except Exception as e:
            raise Exception(f"评估过程出错: {str(e)}")

    def _find_shp_file(self, folder_path):
        """在文件夹中查找第一个.shp文件"""
        try:
            shp_files = glob.glob(os.path.join(folder_path, "*.shp"))
            if not shp_files:
                raise Exception(f"在文件夹 {folder_path} 中未找到shp文件")
            return shp_files[0]  # 返回找到的第一个shp文件路径
        except Exception as e:
            raise Exception(f"查找shp文件时出错: {str(e)}")

    def _calculate_roof_area(self, vector_path):
        """计算屋顶总面积"""
        try:
            # 如果是文件夹，先找到shp文件
            if os.path.isdir(vector_path):
                shp_path = self._find_shp_file(vector_path)
            else:
                shp_path = vector_path
                
            gdf = gpd.read_file(shp_path)
            # 确保使用投影坐标系统计算面积
            if not gdf.crs or gdf.crs.is_geographic:
                gdf = gdf.to_crs('EPSG:3857')  # 墨卡托投影
            total_area = gdf.geometry.area.sum()
            return total_area
        except Exception as e:
            raise Exception(f"计算屋顶面积时出错: {str(e)}")

    def _get_study_area_bounds(self, vector_path):
        """获取研究区域的经纬度范围"""
        try:
            # 如果是文件夹，先找到shp文件
            if os.path.isdir(vector_path):
                shp_path = self._find_shp_file(vector_path)
            else:
                shp_path = vector_path
                
            gdf = gpd.read_file(shp_path)
            if not gdf.crs.is_geographic:
                gdf = gdf.to_crs('EPSG:4326')  # 转换为地理坐标系
            bounds = gdf.total_bounds  # (minx, miny, maxx, maxy)
            return bounds
        except Exception as e:
            raise Exception(f"获取研究区域范围时出错: {str(e)}")

    def _calculate_radiation(self, bounds, start_time, end_time, time_scale):
        """计算指定区域和时间范围内的太阳辐射量"""
        try:
            # 解析时间范围
            start_date = datetime.strptime(start_time, '%Y-%m')
            end_date = datetime.strptime(end_time, '%Y-%m')
            
            # 获取时间范围内的辐射数据文件
            radiation_files = []
            for file in glob.glob(os.path.join(self.radiation_folder, '*.tif')):
                file_date = self._parse_date_from_filename(file)
                if start_date <= file_date <= end_date:
                    radiation_files.append(file)
            
            if not radiation_files:
                raise Exception("未找到指定时间范围内的辐射数据")
            
            # 计算平均辐射量
            total_radiation = 0
            count = 0
            
            for file in radiation_files:
                with rasterio.open(file) as src:
                    # 裁剪研究区域
                    window = src.window(*bounds)
                    data = src.read(1, window=window)
                    
                    # 计算区域平均值
                    valid_data = data[data != src.nodata]
                    if len(valid_data) > 0:
                        total_radiation += np.mean(valid_data)
                        count += 1
            
            if count == 0:
                raise Exception("未能获取有效的辐射数据")
                
            average_radiation = total_radiation / count
            
            # 根据时间尺度调整
            if time_scale == 'year':
                average_radiation *= 365 * 24  # 转换为年辐射量
            elif time_scale == 'month':
                average_radiation *= 30 * 24   # 转换为月辐射量
                
            return average_radiation
            
        except Exception as e:
            raise Exception(f"计算辐射量时出错: {str(e)}")

    def _parse_date_from_filename(self, filename):
        """从文件名解析日期"""
        # 假设文件名格式为: ISCCP_HXG_total_PAR_YYYY_MM_DD_HH.tif
        basename = os.path.basename(filename)
        parts = basename.split('_')
        year = int(parts[4])
        month = int(parts[5])
        return datetime(year, month, 1)

# 使用示例
if __name__ == "__main__":
    # 初始化模型
    model = RoofPVCarbonModel(
        radiation_folder="2018tif",
        system_efficiency=0.8,
        pv_efficiency=0.2  # 默认光伏转换效率
    )
    
    # 运行评估
    result = model.evaluate(
        roof_vector_path="/Users/mpl/Downloads/coding/project/work/ogmsgui/experiment/Nanjing rooftop",
        emission_factor=0.8794,
        start_time="2018-01",
        end_time="2018-12",
        time_scale="year"
        # 不传入pv_efficiency则使用默认值
    )
    
    # 打印结果
    print(f"年碳减排潜力: {result['carbon_reduction']:.2f} 吨CO2")
    print(f"年发电量预测: {result['power_generation']:.2f} kWh")
    print("\n详细参数:")
    for key, value in result['parameters'].items():
        print(f"{key}: {value}") 