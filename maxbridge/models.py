from dataclasses import dataclass
from typing import Optional ,List ,Dict ,Any


@dataclass
class User :
    id :int
    name :str
    username :Optional [str ]=None
    avatar :Optional [str ]=None


@dataclass
class Chat :
    id :int
    title :str
    type :str
    participants_count :Optional [int ]=None
    avatar :Optional [str ]=None


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