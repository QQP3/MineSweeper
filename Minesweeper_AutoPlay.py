FLAGGED = 'F'
UNSEEN = '#'

def check(board, t, k, m, n):
    target_number = board[t][k]
    if target_number == UNSEEN or target_number == FLAGGED:
        return -1
    target_number = int(target_number) - int('0')
    status = -1
    coordinates = (-1, -1)
    unseen = []
    flagged = 0
    candidates = []
    
    for i in range(t - 1, t + 2):
        for j in range(k - 1, k + 2):
            if i >= 0 and j >= 0 and i < m and j < n:
                if board[i][j] == FLAGGED:
                    flagged += 1
                if board[i][j] == UNSEEN:
                    unseen.append((i, j))
    
    if len(unseen) != 0:
        if flagged == target_number:
            return (0, unseen)
        if target_number - flagged == len(unseen):
            return (1, unseen)
    return -1
    
    
    
            
                    
                    
#This function returns bool  (1 for flagging the squer and 0 for pressing the squer) and a tupel for the coordinates
def solution(board, m, n):
    doomsday_plan = (-1, -1)
    for i in range(m):
        for j in range(n):
            result = check(board, i, j, m, n)
            if board[i][j] == UNSEEN:
                doomsday_plan = (i, j)
            if result != -1:
                return result
    if doomsday_plan == (-1, -1):
        raise Exception("SOLUTION FUNCTION FAILUER: There is no unseen squer left!")
    return (0, [doomsday_plan])
