import tkinter 

window = tkinter.Tk()
window.attributes('-topmost',True)
window.title("memo_jang")
window.geometry("320x800+820+100")
window.resizable(True,True)

entry = tkinter.Text(width=60, height=50)
entry.pack()

window.mainloop()