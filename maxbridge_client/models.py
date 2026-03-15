from dataclasses import dataclass
from typing import Optional ,List ,Dict ,Any


@dataclass
class User :
    id :int
    name :str
    username :Optional [str ]=None
    avatar :Optional [str ]=None

    @classmethod
    def from_raw (cls ,raw :Dict [str ,Any ]):
        contact_id =raw .get ("id")
        names =raw .get ("names")or []
        name =names [0 ].get ("name") if names else str (contact_id )
        username =raw .get ("username")
        base_url =raw .get ("baseUrl") or raw .get ("baseRawUrl")
        avatar =None
        if base_url :
            avatar =base_url
        return cls (
        id =contact_id ,
        name =name ,
        username =username ,
        avatar =avatar ,
        )


@dataclass
class Chat :
    id :int
    title :str
    type :str
    participants_count :Optional [int ]=None
    avatar :Optional [str ]=None

    @classmethod
    def from_raw (cls ,raw :Dict [str ,Any ]):
        chat_id =raw .get ("id")
        title =raw .get ("title")
        chat_type =raw .get ("type","UNKNOWN")
        participants =raw .get ("participants")or {}
        participants_count =len (participants )
        avatar =raw .get ("avatar") or raw .get ("baseUrl") or raw .get ("baseRawUrl")
        if not title and chat_type =='DIALOG':
            # диалоги обычно без своего title, его удобно подставлять снаружи по собеседнику
            title =f"Dialog {chat_id }"
        return cls (
        id =chat_id ,
        title =title or "" ,
        type =chat_type ,
        participants_count =participants_count or None ,
        avatar =avatar ,
        )


@dataclass
class Message :
    id :str
    chat_id :int
    user_id :int
    text :str
    timestamp :int
    attaches :List [Dict [str ,Any ]]=None

    def __post_init__ (self ):
        if self .attaches is None :
            self .attaches =[]

    @classmethod
    def from_raw (cls ,raw :Dict [str ,Any ] ,chat_id :Optional [int ]=None ):
        return cls (
        id =raw .get ("id" ),
        chat_id =chat_id if chat_id is not None else int (raw .get ("chatId" ,0 )),
        user_id =raw .get ("sender" ),
        text =raw .get ("text" ,""),
        timestamp =raw .get ("time" ,0 ),
        attaches =raw .get ("attaches" )or [],
        )