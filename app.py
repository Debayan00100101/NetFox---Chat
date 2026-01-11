import streamlit as st
from supabase import create_client
import base64
import time
import json

SUPABASE_URL = "https://fsptnphfomjcdjmcvpxb.supabase.co"
SUPABASE_KEY = "sb_publishable_wTFouimTBdHzMKwkxXf5LQ_REaR0AOO"
db = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(layout="wide")

# --------- THEME SWITCH ---------
bg = "#0e0e16"
if "page" in st.session_state and st.session_state.page == "home":
    bg = "linear-gradient(135deg,#4b1b7a,#220a40)"

st.markdown(f"""
<style>
html, body, [data-testid="stApp"] {{
    height:100%;
    background:{bg};
    color:white;
}}
input, textarea {{ background:#2b0f47!important; color:white!important; border-radius:12px!important; }}
button {{ background:#6b2fbf!important; color:white!important; border-radius:12px!important; }}
.chatbox {{
    background:#1c0d2e;
    padding:12px;
    border-radius:14px;
    margin-bottom:10px;
}}
.profile-card {{
    background:#1c0d2e;
    padding:20px;
    border-radius:16px;
    text-align:center;
}}
.avatar {{ width:90px; height:90px; border-radius:50%; }}
</style>
""", unsafe_allow_html=True)

# ---------------- STATE ----------------
for k,v in {
    "user":None,
    "page":"home",
    "view_profile":None
}.items():
    if k not in st.session_state:
        st.session_state[k]=v

# ---------------- LOGIN ----------------
if not st.session_state.user:
    st.title("NetFox")
    gp=st.text_input("Global password",type="password")
    username=st.text_input("Username")
    bio=st.text_input("Bio")
    avatar=st.file_uploader("Avatar")

    if st.button("Enter"):
        if gp!="super00100101":
            st.error("Wrong password")
        else:
            data=db.table("users").select("*").eq("username",username).execute().data
            if data:
                st.session_state.user=data[0]
            else:
                av=base64.b64encode(avatar.read()).decode() if avatar else ""
                new=db.table("users").insert({"username":username,"bio":bio,"avatar":av}).execute()
                st.session_state.user=new.data[0]
            st.rerun()

# ---------------- MAIN ----------------
else:
    u=st.session_state.user

    with st.sidebar:
        if u["avatar"]:
            st.image(base64.b64decode(u["avatar"]),width=80)
        st.markdown(f"### {u['username']}")
        if st.button("Home"): st.session_state.page="home"
        if st.button("Friends"): st.session_state.page="friends"
        if st.button("Notifications"): st.session_state.page="notif"
        if st.button("Me"): st.session_state.page="me"
        if st.button("Logout"):
            st.session_state.user=None
            st.rerun()

    # ---------------- HOME ----------------
    if st.session_state.page=="home":
        st.header("NetFox")

        msgs=db.table("messages").select("*").order("time").execute().data

        for m in msgs:
            if m.get("deleted"): continue
            if str(u["id"]) in (m.get("deleted_by") or []): continue

            sender=db.table("users").select("*").eq("id",m["from_user"]).execute().data[0]
            reactions=m.get("reactions") or {}

            st.markdown(f"""
            <div class='chatbox'>
            <img src="data:image/png;base64,{sender['avatar']}" width=32 style="border-radius:50%">
            <b>{sender['username']}</b><br>{m['text']}
            </div>
            """,unsafe_allow_html=True)

            cols=st.columns(5)
            for i,emo in enumerate(["❤️","😂","👍","🔥","😭"]):
                if cols[i].button(emo,key=f"r{emo}{m['id']}"):
                    reactions.setdefault(emo,[])
                    if u["id"] not in reactions[emo]:
                        reactions[emo].append(u["id"])
                    db.table("messages").update({"reactions":reactions}).eq("id",m["id"]).execute()
                    st.rerun()

            if reactions:
                st.caption(" ".join([f"{k}{len(v)}" for k,v in reactions.items()]))

            c1,c2=st.columns(2)
            if c1.button("Delete for me",key=f"d{m['id']}"):
                db.table("messages").update({"deleted_by":(m.get("deleted_by") or [])+[str(u["id"])]}).eq("id",m["id"]).execute()
                st.rerun()

            if m["from_user"]==u["id"]:
                if c2.button("Unsend",key=f"u{m['id']}"):
                    db.table("messages").update({"deleted":True}).eq("id",m["id"]).execute()
                    st.rerun()

        msg=st.chat_input("Type message…")
        if msg:
            db.table("messages").insert({"from_user":u["id"],"text":msg}).execute()
            st.rerun()

    # ---------------- FRIENDS ----------------
    if st.session_state.page=="friends":
        if st.session_state.view_profile:
            p=st.session_state.view_profile
            rel=db.table("follows").select("*").eq("from_user",u["id"]).eq("to_user",p["id"]).execute().data
            followed=bool(rel)

            st.markdown(f"""
            <div class='profile-card'>
            <img src="data:image/png;base64,{p['avatar']}" class='avatar'><br>
            <h2>{p['username']}</h2>
            <p>{p.get('bio','')}</p>
            </div>
            """,unsafe_allow_html=True)

            if not followed:
                if st.button("Follow"):
                    db.table("follows").insert({"from_user":u["id"],"to_user":p["id"]}).execute()
                    st.rerun()
            else:
                if st.button("Unfollow"):
                    db.table("follows").delete().eq("from_user",u["id"]).eq("to_user",p["id"]).execute()
                    st.rerun()

            if st.button("Back"):
                st.session_state.view_profile=None
                st.rerun()

        else:
            st.header("Find Users")
            s=st.text_input("Search")

            if s:
                users=db.table("users").select("*").ilike("username",f"%{s}%").execute().data
                for x in users:
                    if st.button(x["username"],key=f"search{x['id']}"):
                        st.session_state.view_profile=x
                        st.rerun()

            st.subheader("Following")
            friends=db.table("follows").select("*").eq("from_user",u["id"]).execute().data
            for i,f in enumerate(friends):
                user=db.table("users").select("*").eq("id",f["to_user"]).execute().data[0]
                if st.button(user["username"],key=f"follow{i}_{user['id']}"):
                    st.session_state.view_profile=user
                    st.rerun()

    # ---------------- NOTIFICATIONS ----------------
    if st.session_state.page=="notif":
        st.header("Notifications")

        rows=db.table("follows").select("*").eq("to_user",u["id"]).execute().data

        for r in rows:
            sender=db.table("users").select("username,avatar").eq("id",r["from_user"]).execute().data[0]
            st.markdown(f"""
            <div class='chatbox'>
            <img src="data:image/png;base64,{sender['avatar']}" width=30 style="border-radius:50%">
            <b>{sender['username']}</b> started following you
            </div>
            """,unsafe_allow_html=True)

    # ---------------- PROFILE ----------------
    if st.session_state.page=="me":
        st.header("My Profile")
        newbio=st.text_input("New bio")
        newav=st.file_uploader("New avatar")

        if st.button("Save"):
            data={}
            if newbio: data["bio"]=newbio
            if newav: data["avatar"]=base64.b64encode(newav.read()).decode()
            if data:
                db.table("users").update(data).eq("id",u["id"]).execute()
                st.success("Updated")
                time.sleep(0.6)
                st.rerun()
