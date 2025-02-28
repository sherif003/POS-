# app.py
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

# Set page config
st.set_page_config(page_title="نظام نقاط البيع - متجر ستوتا", layout="wide")

# Initialize data files
DATA_PATH = "stota_data"
if not os.path.exists(DATA_PATH):
    os.makedirs(DATA_PATH)

PRODUCTS_FILE = os.path.join(DATA_PATH, "products.csv")
ORDERS_FILE = os.path.join(DATA_PATH, "orders.csv")

# Load or initialize data
def load_data():
    try:
        products = pd.read_csv(PRODUCTS_FILE)
    except:
        products = pd.DataFrame(columns=["معرف المنتج", "اسم المنتج", "السعر الأصلي", "سعر البيع", "المخزون"])
    
    try:
        orders = pd.read_csv(ORDERS_FILE)
    except:
        orders = pd.DataFrame(columns=["معرف الطلب", "التاريخ", "المنتجات", "الإجمالي"])
    
    return products, orders

# Save data
def save_data(products, orders):
    products.to_csv(PRODUCTS_FILE, index=False)
    orders.to_csv(ORDERS_FILE, index=False)

# Sidebar menu
with st.sidebar:
    selected = option_menu(
        "القائمة الرئيسية",
        ["المنتجات", "الطلبات", "الرؤى والإحصاءيات", "التصدير"],
        icons=["box", "cart", "bar-chart", "download"],
        menu_icon="shop",
        default_index=0,
    )

products, orders = load_data()

# Pages
if selected == "المنتجات":
    st.header("إدارة المنتجات")
    
    tab1, tab2 = st.tabs(["إضافة منتج", "تعديل المنتجات"])
    
    with tab1:
        with st.form("add_product"):
            product_id = st.text_input("معرف المنتج")
            product_name = st.text_input("اسم المنتج")
            original_price = st.number_input("السعر الأصلي", min_value=0.0)
            selling_price = st.number_input("سعر البيع", min_value=0.0)
            stock = st.number_input("المخزون", min_value=0, step=1)
            
            if st.form_submit_button("إضافة"):
                new_product = pd.DataFrame({
                    "معرف المنتج": [product_id],
                    "اسم المنتج": [product_name],
                    "السعر الأصلي": [original_price],
                    "سعر البيع": [selling_price],
                    "المخزون": [stock]
                })
                products = pd.concat([products, new_product])
                save_data(products, orders)
                st.success("تمت إضافة المنتج بنجاح!")
    
    with tab2:
        if not products.empty:
            st.dataframe(products)
            product_to_edit = st.selectbox("اختر المنتج للتعديل", products["معرف المنتج"])
            product_data = products[products["معرف المنتج"] == product_to_edit].iloc[0]
            
            with st.form("edit_product"):
                new_name = st.text_input("اسم المنتج", value=product_data["اسم المنتج"])
                new_original = st.number_input("السعر الأصلي", value=float(product_data["السعر الأصلي"]))
                new_selling = st.number_input("سعر البيع", value=float(product_data["سعر البيع"]))
                new_stock = st.number_input("المخزون", value=int(product_data["المخزون"]))
                
                if st.form_submit_button("حفظ التعديلات"):
                    products.loc[products["معرف المنتج"] == product_to_edit] = [
                        product_to_edit, new_name, new_original, new_selling, new_stock
                    ]
                    save_data(products, orders)
                    st.success("تم تعديل المنتج بنجاح!")

elif selected == "الطلبات":
    st.header("إدارة الطلبات")
    
    tab1, tab2 = st.tabs(["طلب جديد", "تعديل الطلبات"])
    
    with tab1:
        with st.form("new_order"):
            order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
            selected_products = st.multiselect("اختر المنتجات", products["اسم المنتج"])
            quantities = {p: st.number_input(f"الكمية لـ {p}", min_value=1, step=1) 
                         for p in selected_products}
            
            if st.form_submit_button("إنشاء الطلب"):
                total = 0
                order_details = []
                for prod in selected_products:
                    price = products[products["اسم المنتج"] == prod]["سعر البيع"].iloc[0]
                    qty = quantities[prod]
                    total += price * qty
                    order_details.append(f"{prod}: {qty}")
                    
                    # Update stock
                    products.loc[products["اسم المنتج"] == prod, "المخزون"] -= qty
                
                new_order = pd.DataFrame({
                    "معرف الطلب": [order_id],
                    "التاريخ": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    "المنتجات": [" | ".join(order_details)],
                    "الإجمالي": [total]
                })
                orders = pd.concat([orders, new_order])
                save_data(products, orders)
                st.success("تم إنشاء الطلب بنجاح!")
    
    with tab2:
        if not orders.empty:
            st.dataframe(orders)

elif selected == "الرؤى والإحصاءيات":
    st.header("الرؤى والإحصاءيات")
    
    if not orders.empty and not products.empty:
        col1, col2, col3 = st.columns(3)
        total_income = orders["الإجمالي"].sum()
        total_cost = sum(products["السعر الأصلي"] * (products["المخزون"].max() - products["المخزون"]))
        net_profit = total_income - total_cost
        
        with col1:
            st.metric("إجمالي الدخل", f"{total_income:,.2f} ريال")
        with col2:
            st.metric("صافي الربح", f"{net_profit:,.2f} ريال")
        with col3:
            st.metric("إجمالي التكاليف", f"{total_cost:,.2f} ريال")
        
        # Charts
        fig1 = px.pie(orders, values="الإجمالي", names="معرف الطلب", title="توزيع المبيعات حسب الطلب")
        st.plotly_chart(fig1)
        
        products_sold = orders["المنتجات"].str.split(" | ", expand=True).stack().value_counts()
        fig2 = px.bar(x=products_sold.index, y=products_sold.values, title="المنتجات الأكثر مبيعاً")
        st.plotly_chart(fig2)

elif selected == "التصدير":
    st.header("تصدير البيانات")
    
    export_type = st.selectbox("اختر نوع البيانات للتصدير", ["المنتجات", "الطلبات", "الكل"])
    
    if st.button("تصدير إلى CSV"):
        if export_type == "المنتجات":
            products.to_csv("exported_products.csv", index=False)
            st.download_button("تحميل الملف", data=open("exported_products.csv", "rb"), 
                             file_name="exported_products.csv")
        elif export_type == "الطلبات":
            orders.to_csv("exported_orders.csv", index=False)
            st.download_button("تحميل الملف", data=open("exported_orders.csv", "rb"), 
                             file_name="exported_orders.csv")
        else:
            with pd.ExcelWriter("stota_full_data.xlsx") as writer:
                products.to_excel(writer, sheet_name="المنتجات", index=False)
                orders.to_excel(writer, sheet_name="الطلبات", index=False)
            st.download_button("تحميل الملف", data=open("stota_full_data.xlsx", "rb"), 
                             file_name="stota_full_data.xlsx")
        st.success("تم التصدير بنجاح!")
