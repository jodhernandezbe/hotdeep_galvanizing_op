
%% Simulation for initial conditions of each bath
% For: Jose Daniel Hernandez Betancur
% Mater thesis title: "Detection of the critcal points of hot-dip galvanizing process:
% a focus on sustainability and sustainable development
% Master degree's name: Master in Engineering - Materials and Processes
% University: National University of Colombia - Medellin branch
% Date: 04 October, 2017
%%-----------------------------------------------------------------------------------------------------------

function [Vol,C_solution,T_solution,m_sln] = initial_conditions(N)

% All tanks have 7 m of length x 1 m width x 2 m depth

% N is a number to indentify the process' step:
% (1) Degreasing
% (2) Normal Pickling
% (3) Abnormal Pickling
% (4) Fluxing

Vol = (2- 0.2*rand())*1*7; % tank's volume [m3]

if N == 1

% 1: NaOH
% 2: H2O
% 3: Grycerol
% 4: Sodium Carboxylates

C_solution = zeros(1,4);

C_solution(1) = 2*rand() + 14; % Measurement instrument's tolerance 1 %
T_solution = 2.2*rand() + 48.9; % Temperature [oC]
C_solution(2) = 100 - C_solution(1);

elseif N == 2

% 1: HCl
% 2: H2O
% 3: Fe2+

C_solution = zeros(1,3);

C_solution(1) = 2*rand() + 16;
C_solution(2) = 100 - C_solution(1);

elseif N == 3

% 1: HCl
% 2: H2O
% 3: Fe2+
% 4: Zn2+

C_solution = zeros(1,4);

C_solution(1) = 2*rand() + 2;
C_solution(2) = 100 - C_solution(1);

elseif N == 4

% 1: Cl-
% 2: Zn2+
% 3: Zn(OH)2
% 4: NH4+
% 5: H2O
% 6: NH4OH
% 7: H+
% 8: Fe
% 9: Fe(OH)2

% As mZnCl2/mNH4Cl = 0.6/0.4

T_solution = 2.2*rand() + 48.9;
m_salt = 400*Vol;
m_sln = 1030*Vol;
CZn_o = 0.6*400*(1/136.315);
CNH4_o = 0.4*400*(1/53.4913);
CH2O_o = (m_sln - m_salt)/(18.0152*Vol);

pH = norminv(rand(),4.5,0.1667);
CH = 10^(-pH);

k1 = 4.9e-12*exp((78680.0/8.3145)*(1/298.15 - 1/(T_solution + 273.15)));
k2 = 5.6e-10*exp((52140.0/8.3145)*(1/298.15 - 1/(T_solution + 273.15)));

A = k1 + k2^2;
B = 2*(k1*CZn_o - (k2^2)*CNH4_o) - (k1 + k2^2)*CH;
C = (2*k1*CH + (k2^2)*CNH4_o)*CNH4_o;
D = - (k2^2)*CH*CNH4_o^2;
p = [A B C D];
r = roots(p);

nn = 0;
for i = 1:length(r)

if imag(r(i)) == 0

nn = nn + 1;
rr(nn) = r(i);

end

end

clear i

% As CZn(OH)2 = eta 1 then eta > 0

mm = 0;
for j = 1:length(rr)

if rr(j) > 0

mm = mm + 1;
rrr(mm) = rr(j);

end

end

tol = 1;
jj = 0;
while tol > 1e-4

jj = jj + 1;
eta2 = rrr(jj);
eta1 = (CH - eta2)/2;

CZn = CZn_o - eta1;
CZnOH2 = eta1;
CH2O = CH2O_o - 2*eta1 - eta2;
CNH4OH = eta2;
CNH4 = CNH4_o - eta2;

CmZn = CZn*65.409;
CmNH4OH = CNH4OH*35.0456;
CmH = CH*1.0079;
CmNH4 = CNH4*18.0383;
CmCl = CZn_o*2*35.453 + CNH4_o*35.453;
CmH2O = CH2O*18.0152;
CmZnOH2 = CZnOH2*99.4236;
m_sln_aux = (CmZn + CmNH4OH + CmH + CmNH4 + CmCl + CmH2O + CmZnOH2)*Vol;

tol = abs(m_sln_aux - m_sln);

end

C_solution = [CmCl CmZn CmZnOH2 CmNH4 CmH2O CmNH4OH CmH 0 0]*(100*Vol/m_sln);

end

return
