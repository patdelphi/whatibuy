import React, { useEffect, useState } from 'react';
import { api, Order } from '../services/api';
import { Search, Filter, Calendar, ChevronLeft, ChevronRight, Download } from 'lucide-react';

export const Orders: React.FC = () => {
    const [orders, setOrders] = useState<Order[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [platformFilter, setPlatformFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    
    // Pagination and Filtering State
    const [page, setPage] = useState(1);
    const [total, setTotal] = useState(0);
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const limit = 100;

    useEffect(() => {
        const fetchOrders = async () => {
            setLoading(true);
            try {
                const data = await api.getOrders(
                    page, 
                    limit, 
                    platformFilter || undefined, 
                    statusFilter || undefined,
                    searchTerm || undefined,
                    startDate || undefined,
                    endDate || undefined
                );
                setOrders(data.items);
                setTotal(data.total);
            } catch (error) {
                console.error("Failed to fetch orders:", error);
            } finally {
                setLoading(false);
            }
        };

        const debounce = setTimeout(fetchOrders, 300);
        return () => clearTimeout(debounce);
    }, [searchTerm, platformFilter, statusFilter, page, startDate, endDate]);

    // Reset page when filters change
    useEffect(() => {
        setPage(1);
    }, [searchTerm, platformFilter, statusFilter, startDate, endDate]);

    const handleExport = () => {
        const url = api.exportOrders(
            platformFilter || undefined, 
            statusFilter || undefined,
            searchTerm || undefined,
            startDate || undefined,
            endDate || undefined
        );
        window.open(url, '_blank');
    };

    const totalPages = Math.ceil(total / limit);

    return (
        <div className="space-y-6">
            {/* Filters */}
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex flex-wrap gap-4 items-center justify-between">
                <div className="flex flex-wrap gap-4 flex-1">
                    <div className="flex items-center gap-2 bg-gray-50 px-3 py-2 rounded-lg border border-gray-200 w-64">
                        <Search size={20} className="text-gray-400" />
                        <input 
                            type="text" 
                            placeholder="搜索商品名称、订单号..." 
                            className="bg-transparent border-none outline-none text-sm w-full"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    
                    <div className="flex items-center gap-2">
                        <Filter size={18} className="text-gray-500" />
                        <select 
                            className="bg-gray-50 border border-gray-200 text-sm rounded-lg p-2 outline-none"
                            value={platformFilter}
                            onChange={(e) => setPlatformFilter(e.target.value)}
                        >
                            <option value="">所有平台</option>
                            <option value="taobao">淘宝</option>
                            <option value="jd">京东</option>
                        </select>
                    </div>

                    <div className="flex items-center gap-2">
                        <Filter size={18} className="text-gray-500" />
                        <select 
                            className="bg-gray-50 border border-gray-200 text-sm rounded-lg p-2 outline-none"
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                        >
                            <option value="">所有状态</option>
                            <option value="交易成功">交易成功</option>
                            <option value="已完成">已完成 (京东)</option>
                            <option value="待发货">待发货</option>
                            <option value="待付款">待付款</option>
                            <option value="交易关闭">交易关闭</option>
                            <option value="已取消">已取消 (京东)</option>
                            <option value="已签收">已签收</option>
                            <option value="双方已评">双方已评</option>
                        </select>
                    </div>

                    <div className="flex items-center gap-2">
                        <Calendar size={18} className="text-gray-500" />
                        <input 
                            type="date" 
                            className="bg-gray-50 border border-gray-200 text-sm rounded-lg p-2 outline-none"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            title="开始日期"
                        />
                        <span className="text-gray-400">-</span>
                        <input 
                            type="date" 
                            className="bg-gray-50 border border-gray-200 text-sm rounded-lg p-2 outline-none"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            title="结束日期"
                        />
                    </div>
                </div>

                <button 
                    onClick={handleExport}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
                >
                    <Download size={18} />
                    导出 CSV
                </button>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left text-gray-500">
                        <thead className="text-xs text-gray-700 uppercase bg-gray-50">
                            <tr>
                                <th scope="col" className="px-6 py-3">日期</th>
                                <th scope="col" className="px-6 py-3">商品信息</th>
                                <th scope="col" className="px-6 py-3">店铺</th>
                                <th scope="col" className="px-6 py-3">金额</th>
                                <th scope="col" className="px-6 py-3">状态</th>
                                <th scope="col" className="px-6 py-3">平台</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr>
                                    <td colSpan={6} className="text-center py-8">加载中...</td>
                                </tr>
                            ) : orders.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="text-center py-8">没有找到相关订单</td>
                                </tr>
                            ) : (
                                orders.map((order) => (
                                    <tr key={order.id} className="bg-white border-b hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            {order.order_date}
                                            <div className="text-xs text-gray-400 mt-1">{order.order_id}</div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex flex-col gap-1">
                                                {order.items.map((item, idx) => (
                                                    <div key={idx} className="flex items-start gap-2 max-w-xs">
                                                        <span className="font-medium text-gray-900 truncate" title={item.title}>
                                                            {item.title || "未知商品"}
                                                        </span>
                                                        <span className="text-xs text-gray-400 whitespace-nowrap">x{item.quantity}</span>
                                                    </div>
                                                ))}
                                                {order.items.length === 0 && <span className="text-gray-400 italic">无商品详情</span>}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 font-medium text-gray-900">
                                            {order.shop_name}
                                        </td>
                                        <td className="px-6 py-4 font-bold text-gray-900">
                                            ¥{order.total_price?.toFixed(2)}
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="bg-green-100 text-green-800 text-xs font-medium px-2.5 py-0.5 rounded">
                                                {order.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`text-xs font-medium px-2.5 py-0.5 rounded ${
                                                order.platform.toLowerCase() === 'taobao' ? 'bg-orange-100 text-orange-800' :
                                                order.platform.toLowerCase() === 'jd' ? 'bg-red-100 text-red-800' :
                                                'bg-gray-100 text-gray-800'
                                            }`}>
                                                {order.platform.toLowerCase() === 'taobao' ? '淘宝' : order.platform.toLowerCase() === 'jd' ? '京东' : order.platform}
                                            </span>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-between">
                    <span className="text-sm text-gray-700">
                        显示 <span className="font-semibold">{(page - 1) * limit + 1}</span> 到 <span className="font-semibold">{Math.min(page * limit, total)}</span> 条，共 <span className="font-semibold">{total}</span> 条
                    </span>
                    <div className="flex items-center gap-2">
                        <button 
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="p-2 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <ChevronLeft size={18} />
                        </button>
                        <span className="text-sm font-medium text-gray-700">
                            第 {page} 页 / 共 {totalPages || 1} 页
                        </span>
                        <button 
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page >= totalPages}
                            className="p-2 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <ChevronRight size={18} />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
