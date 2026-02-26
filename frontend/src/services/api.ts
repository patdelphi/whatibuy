import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export interface OrderItem {
    title: string;
    price: number;
    quantity: number;
    sku_info?: string;
    image_url?: string;
}

export interface Order {
    id: number;
    order_id: string;
    order_date: string;
    status: string;
    shop_name: string;
    total_price: number;
    currency: string;
    platform: string;
    items: OrderItem[];
}

export interface ConsumptionStats {
    total_spent: number;
    order_count: number;
    platform_breakdown: Record<string, number>;
    monthly_breakdown: Record<string, number>;
}

export interface OrderListResponse {
    items: Order[];
    total: number;
    page: number;
    limit: number;
}

export const api = {
    getOrders: async (page = 1, limit = 100, platform?: string, search?: string, startDate?: string, endDate?: string) => {
        const params: any = { page, limit };
        if (platform) params.platform = platform;
        if (search) params.search = search;
        if (startDate) params.start_date = startDate;
        if (endDate) params.end_date = endDate;
        
        const response = await axios.get<OrderListResponse>(`${API_BASE_URL}/orders`, { params });
        return response.data;
    },
    
    getStats: async (startDate?: string, endDate?: string) => {
        const params: any = {};
        if (startDate) params.start_date = startDate;
        if (endDate) params.end_date = endDate;
        
        const response = await axios.get<ConsumptionStats>(`${API_BASE_URL}/stats`, { params });
        return response.data;
    }
};
