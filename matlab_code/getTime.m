function Time = getTime(Y,Zone)
%Y is the gregorian year
%Zone is the timezone relative to UTC. EST is -5, CST is -6, MST is -7, PST
%is -8
Time.year = Y*ones(525600,1);
Time.month = [1*ones(44640,1);2*ones(40320,1);3*ones(44640,1);4*ones(43200,1);5*ones(44640,1);6*ones(43200,1);7*ones(44640,1);8*ones(44640,1);9*ones(43200,1);10*ones(44640,1);11*ones(43200,1);12*ones(44640,1)];

Time.day = zeros(525600,1);
Time.hour = mod(floor(((1:525600)'-1)/60),24);
Time.minute = mod(((1:525600)'-1),60);
Time.second = zeros(525600,1);
Time.UTCOffset = Zone*ones(525600,1);


%January
for i = 1:31
    for j = 1:1440
        Time.day((i-1)*1440+j) = i;
    end
end
%February
for i = 32:59
    for j = 1:1440
        Time.day((i-1)*1440+j) = i-31;
    end
end
%March
for i = 60:90
    for j = 1:1440
        Time.day((i-1)*1440+j) = i-59;
    end
end
%April
for i = 91:120
    for j = 1:1440
        Time.day((i-1)*1440+j) = i-90;
    end
end
%May
for i = 121:151
    for j = 1:1440
        Time.day((i-1)*1440+j) = i-120;
    end
end
%June
for i = 152:181
    for j = 1:1440
        Time.day((i-1)*1440+j) = i-151;
    end
end

%July
for i = 182:212
    for j = 1:1440
        Time.day((i-1)*1440+j) = i-181;
    end
end

%August
for i = 213:243
    for j = 1:1440
        Time.day((i-1)*1440+j) = i-212;
    end
end

%September
for i = 244:273
    for j = 1:1440
        Time.day((i-1)*1440+j) = i-243;
    end
end

%October
for i = 274:304
    for j = 1:1440
        Time.day((i-1)*1440+j) = i-273;
    end
end

%November
for i = 305:334
    for j = 1:1440
        Time.day((i-1)*1440+j) = i-304;
    end
end

%December
for i = 335:365
    for j = 1:1440
        Time.day((i-1)*1440+j) = i-334;
    end
end

return
end
