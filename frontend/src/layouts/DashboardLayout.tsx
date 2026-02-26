import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, ShoppingBag, Settings, Menu } from 'lucide-react';
import { clsx } from 'clsx';

interface DashboardLayoutProps {
    children: React.ReactNode;
}

const SidebarItem = ({ to, icon: Icon, label }: { to: string, icon: any, label: string }) => {
    const location = useLocation();
    const isActive = location.pathname === to;
    
    return (
        <Link 
            to={to} 
            className={clsx(
                "flex items-center gap-3 px-4 py-3 rounded-lg transition-colors",
                isActive ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100"
            )}
        >
            <Icon size={20} />
            <span className="font-medium">{label}</span>
        </Link>
    );
};

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
    return (
        <div className="flex h-screen bg-gray-50">
            {/* Sidebar */}
            <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
                <div className="p-6 border-b border-gray-100">
                    <h1 className="text-2xl font-bold text-blue-600 flex items-center gap-2">
                        <ShoppingBag className="text-blue-600" />
                        WhatIBuy
                    </h1>
                </div>
                
                <nav className="flex-1 p-4 space-y-2">
                    <SidebarItem to="/" icon={LayoutDashboard} label="消费分析" />
                    <SidebarItem to="/orders" icon={ShoppingBag} label="订单列表" />
                    {/* <SidebarItem to="/settings" icon={Settings} label="设置" /> */}
                </nav>
                
                <div className="p-4 border-t border-gray-100 text-xs text-gray-400">
                    v0.1.0 Beta
                </div>
            </div>
            
            {/* Main Content */}
            <div className="flex-1 overflow-auto">
                <header className="bg-white border-b border-gray-200 px-8 py-4 flex items-center justify-between sticky top-0 z-10">
                    <h2 className="text-xl font-semibold text-gray-800">
                        {/* Dynamic Title based on route could go here */}
                        控制台
                    </h2>
                    <div className="flex items-center gap-4">
                        <span className="text-sm text-gray-500">欢迎回来</span>
                        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">
                            U
                        </div>
                    </div>
                </header>
                
                <main className="p-8">
                    {children}
                </main>
            </div>
        </div>
    );
};
