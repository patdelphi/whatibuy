import React, { useEffect, useState } from 'react';
import { 
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
    PieChart, Pie, Cell 
} from 'recharts';
import { api, ConsumptionStats } from '../services/api';
import { DollarSign, ShoppingBag, CreditCard, Calendar } from 'lucide-react';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export const Analysis: React.FC = () => {
    const [stats, setStats] = useState<ConsumptionStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [platformFilter, setPlatformFilter] = useState('');

    useEffect(() => {
        const fetchStats = async () => {
            setLoading(true);
            try {
                const data = await api.getStats(
                    startDate || undefined, 
                    endDate || undefined,
                    platformFilter || undefined
                );
                setStats(data);
            } catch (error) {
                console.error("Failed to fetch stats:", error);
            } finally {
                setLoading(false);
            }
        };
        
        const debounce = setTimeout(fetchStats, 500);
        return () => clearTimeout(debounce);
    }, [startDate, endDate, platformFilter]);

    if (loading && !stats) return <div className="flex justify-center items-center h-64">加载中...</div>;
    if (!stats) return <div className="text-red-500">无法加载数据</div>;

    // Prepare data for charts
    const platformData = Object.entries(stats.platform_breakdown).map(([name, value]) => ({
        name: name.toLowerCase() === 'taobao' ? '淘宝' : name.toLowerCase() === 'jd' ? '京东' : name,
        value
    }));

    const monthlyData = Object.entries(stats.monthly_breakdown)
        .sort((a, b) => b[0].localeCompare(a[0])) // Sort by date descending
        .slice(0, 12) // Last 12 months
        .reverse() // Show oldest to newest
        .map(([name, value]) => ({
            name, value
        }));

    return (
        <div className="space-y-6">
            {/* Filters */}
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4">
                <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-600">平台:</span>
                    <select 
                        className="bg-gray-50 border border-gray-300 text-sm rounded-lg p-2 outline-none"
                        value={platformFilter}
                        onChange={(e) => setPlatformFilter(e.target.value)}
                    >
                        <option value="">所有平台</option>
                        <option value="taobao">淘宝</option>
                        <option value="jd">京东</option>
                    </select>
                </div>

                <div className="h-6 w-px bg-gray-200 mx-2"></div>

                <Calendar className="text-gray-500" size={20} />
                <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-600">从</span>
                    <input 
                        type="date" 
                        className="border border-gray-300 rounded px-2 py-1 text-sm"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                    />
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-600">到</span>
                    <input 
                        type="date" 
                        className="border border-gray-300 rounded px-2 py-1 text-sm"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                    />
                </div>
                {(startDate || endDate || platformFilter) && (
                    <button 
                        onClick={() => { setStartDate(''); setEndDate(''); setPlatformFilter(''); }}
                        className="text-xs text-blue-600 hover:underline"
                    >
                        清除筛选
                    </button>
                )}
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4">
                    <div className="p-3 bg-blue-100 text-blue-600 rounded-lg">
                        <DollarSign size={24} />
                    </div>
                    <div>
                        <p className="text-sm text-gray-500">总支出</p>
                        <h3 className="text-2xl font-bold text-gray-800">¥{stats.total_spent.toFixed(2)}</h3>
                    </div>
                </div>

                <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4">
                    <div className="p-3 bg-green-100 text-green-600 rounded-lg">
                        <ShoppingBag size={24} />
                    </div>
                    <div>
                        <p className="text-sm text-gray-500">订单总数</p>
                        <h3 className="text-2xl font-bold text-gray-800">{stats.order_count}</h3>
                    </div>
                </div>
                
                 <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4">
                    <div className="p-3 bg-purple-100 text-purple-600 rounded-lg">
                        <CreditCard size={24} />
                    </div>
                    <div>
                        <p className="text-sm text-gray-500">平均客单价</p>
                        <h3 className="text-2xl font-bold text-gray-800">
                            ¥{(stats.order_count > 0 ? stats.total_spent / stats.order_count : 0).toFixed(2)}
                        </h3>
                    </div>
                </div>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Monthly Trend */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <h3 className="text-lg font-semibold mb-4 text-gray-800">月度支出趋势</h3>
                    <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={monthlyData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis dataKey="name" tick={{fontSize: 12}} />
                                <YAxis tick={{fontSize: 12}} />
                                <Tooltip formatter={(value: number) => [`¥${value.toFixed(2)}`, '支出']} />
                                <Bar dataKey="value" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Platform Distribution */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <h3 className="text-lg font-semibold mb-4 text-gray-800">平台消费占比</h3>
                    <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={platformData}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                    outerRadius={100}
                                    fill="#8884d8"
                                    dataKey="value"
                                >
                                    {platformData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip formatter={(value: number) => [`¥${value.toFixed(2)}`, '支出']} />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
};
